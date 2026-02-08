import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.db import SessionLocal
from app.models import Job, Artifact


def _artifact_dir() -> Path:
    base = os.getenv("ARTIFACT_DIR", "./data")
    Path(base).mkdir(parents=True, exist_ok=True)
    return Path(base)


def _confidence_score(has_pct: bool, is_recent: bool, is_primary: bool, inferred: bool) -> int:
    score = 0
    if is_primary:
        score += 40
    if is_recent:
        score += 20
    if has_pct:
        score += 20
    if inferred:
        score -= 20
    score = max(0, min(100, score))
    return score


def _render_graph_html(job_id: str, nodes: list[dict], edges: list[dict]) -> Path:
    env = Environment(loader=FileSystemLoader("/app/templates"))
    template = env.get_template("graph.html")

    html = template.render(job_id=job_id, nodes=nodes, edges=edges)
    out_path = _artifact_dir() / f"graph_{job_id}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def _render_pdf(job_id: str, siren: str, summary: dict) -> Path:
    out_path = _artifact_dir() / f"report_{job_id}.pdf"
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Ownership Chain Report (MVP)")

    y -= 40
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"SIREN: {siren}")
    y -= 20
    c.drawString(50, y, f"Job ID: {job_id}")
    y -= 20
    c.drawString(50, y, f"Generated at: {datetime.utcnow().isoformat()} UTC")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Summary")

    y -= 20
    c.setFont("Helvetica", 10)
    for key, value in summary.items():
        c.drawString(50, y, f"- {key}: {value}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60

    c.showPage()
    c.save()
    return out_path


def build_ownership(job_id: str) -> None:
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.updated_at = datetime.utcnow()
        session.commit()

        # Placeholder data for v1 scaffold
        nodes = [
            {"id": job.siren, "label": f"Company {job.siren}", "group": "target"},
            {"id": "UNKNOWN", "label": "Actionnaire non public", "group": "unknown"},
        ]
        edges = [
            {"from": "UNKNOWN", "to": job.siren, "label": "N/A", "confidence": 20}
        ]

        confidence = _confidence_score(has_pct=False, is_recent=False, is_primary=False, inferred=True)

        summary = {
            "Direct shareholders found": "0",
            "Missing data": "Yes",
            "Confidence score": str(confidence),
            "Sources": "Sirene (identity only); ownership not public",
        }

        graph_path = _render_graph_html(job.id, nodes, edges)
        pdf_path = _render_pdf(job.id, job.siren, summary)

        session.add(Artifact(job_id=job.id, kind="graph", path=str(graph_path)))
        session.add(Artifact(job_id=job.id, kind="pdf", path=str(pdf_path)))

        job.status = "done"
        job.result_json = {
            "siren": job.siren,
            "depth": job.depth,
            "nodes": nodes,
            "edges": edges,
            "summary": summary,
        }
        job.updated_at = datetime.utcnow()
        session.commit()
    except Exception as exc:
        session.rollback()
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "error"
            job.error = str(exc)
            job.updated_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()
