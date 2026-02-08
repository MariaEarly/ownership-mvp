# Ownership Chain MVP (France)

This project scaffolds a minimal service that accepts a SIREN and produces:
- A graph (interactive HTML)
- A PDF report
- A JSON API response with job status and links

## What this MVP does
- Stores jobs and results in Postgres
- Runs processing asynchronously with RQ (Redis)
- Generates a stub graph and PDF (placeholder data)
- Provides a clean structure to plug real data sources later

## Quick start (Docker)
1. Copy env file:
```bash
cp .env.example .env
```
2. Start services:
```bash
docker compose up --build
```

## API
- `POST /ownership` with body `{ "siren": "552100554", "depth": 3 }`
- `GET /ownership/{job_id}` to get status and artifacts

## Project structure
- `backend/app/main.py`: FastAPI app
- `backend/app/tasks.py`: background job logic
- `backend/app/models.py`: SQLAlchemy models
- `backend/app/db.py`: database session
- `backend/worker.py`: RQ worker entrypoint
- `backend/templates/graph.html`: interactive graph template
- `data/`: generated artifacts (PDF/HTML)

## Notes
- This is an MVP scaffold. Data extraction from Sirene/BODACC is not implemented yet.
- Confidence scoring is included but uses placeholder logic until real sources are wired.

## Sirene integration (identity + siège address)
This MVP can call the INSEE Sirene API if you provide credentials:
- Preferred for API-key plans: set `SIRENE_API_KEY` (portal key).
- Alternative: set `SIRENE_CLIENT_ID` and `SIRENE_CLIENT_SECRET` so the app can fetch a token.
- Alternative: set `SIRENE_ACCESS_TOKEN` (pre-generated token).
- Optional: `SIRENE_TOKEN_URL` (default: `https://api.insee.fr/token`).
- Optional: `SIRENE_SCOPE` if your INSEE account requires it.
- Optional: `SIRENE_BASE_URL` (default: `https://api.insee.fr/api-sirene/3.11`).

## Deploy on Render (free)
1. Create a GitHub repo named `ownership-mvp` under your account.
2. Push this project to that repo.
3. In Render, use **Blueprint** and point to `render.yaml`.
4. Render will create:
   - Web service (API)
   - Postgres
   - Artifacts stored in `/tmp` (ephemeral on free plan)

After deploy, test:
- `POST https://<api-url>/ownership`
- `GET https://<api-url>/ownership/{job_id}`
