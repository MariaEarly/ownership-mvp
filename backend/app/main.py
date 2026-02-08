import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
from app.db import init_db, SessionLocal
from app.models import Job, Artifact
from app.tasks import build_ownership

app = FastAPI(title="Ownership Chain MVP")


class OwnershipRequest(BaseModel):
    siren: str = Field(..., min_length=9, max_length=9)
    depth: int = Field(3, ge=1, le=6)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _queue() -> Queue | None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    redis_conn = Redis.from_url(redis_url)
    return Queue("ownership", connection=redis_conn)


@app.post("/ownership")
def create_ownership(req: OwnershipRequest):
    session = SessionLocal()
    try:
        job = Job(siren=req.siren, depth=req.depth, status="queued")
        session.add(job)
        session.commit()

        q = _queue()
        if q:
            q.enqueue(build_ownership, job.id)
            return {"job_id": job.id, "status": job.status}

        # Synchronous fallback for environments without Redis (e.g., Render free tier).
        build_ownership(job.id)
        session.refresh(job)
        return {"job_id": job.id, "status": job.status}
    finally:
        session.close()


@app.get("/ownership/{job_id}")
def get_ownership(job_id: str):
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="job not found")

        artifacts = session.query(Artifact).filter(Artifact.job_id == job.id).all()
        return {
            "job_id": job.id,
            "siren": job.siren,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "error": job.error,
            "result": job.result_json,
            "artifacts": [
                {"kind": a.kind, "path": a.path, "created_at": a.created_at.isoformat()}
                for a in artifacts
            ],
        }
    finally:
        session.close()


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
