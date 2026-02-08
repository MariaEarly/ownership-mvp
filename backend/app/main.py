import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
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
def get_ownership(job_id: str, request: Request):
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            # Fallback: if artifacts exist on disk, return them even if DB row is missing.
            artifacts = []
            base_url = str(request.base_url).rstrip("/")
            artifact_dir = os.getenv("ARTIFACT_DIR", "/tmp/artifacts")
            pdf_path = os.path.join(artifact_dir, f"report_{job_id}.pdf")
            graph_path = os.path.join(artifact_dir, f"graph_{job_id}.html")
            if os.path.exists(pdf_path):
                artifacts.append(
                    {
                        "kind": "pdf",
                        "path": pdf_path,
                        "url": f"{base_url}/artifact/{job_id}/pdf",
                    }
                )
            if os.path.exists(graph_path):
                artifacts.append(
                    {
                        "kind": "graph",
                        "path": graph_path,
                        "url": f"{base_url}/artifact/{job_id}/graph",
                    }
                )
            if artifacts:
                return {
                    "job_id": job_id,
                    "siren": None,
                    "status": "done",
                    "created_at": None,
                    "updated_at": None,
                    "error": None,
                    "result": None,
                    "artifacts": artifacts,
                }
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


@app.get("/artifact/{job_id}/{kind}")
def get_artifact(job_id: str, kind: str):
    if kind not in {"pdf", "graph"}:
        raise HTTPException(status_code=400, detail="invalid artifact kind")

    artifact_dir = os.getenv("ARTIFACT_DIR", "/tmp/artifacts")
    if kind == "pdf":
        path = os.path.join(artifact_dir, f"report_{job_id}.pdf")
        media_type = "application/pdf"
    else:
        path = os.path.join(artifact_dir, f"graph_{job_id}.html")
        media_type = "text/html"

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="artifact not found")

    return FileResponse(path, media_type=media_type)
