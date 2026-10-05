# Deployment

## Containers (§58)

| Container | Image build | Purpose |
|---|---|---|
| `spa-frontend` | `frontend/Dockerfile` (Next.js standalone) | web application |
| `spa-backend` | `backend/Dockerfile` (FastAPI + ml package) | REST API + inline ML inference |
| `spa-worker` | same as backend, command `python -m app.worker` | batch prediction jobs |
| `spa-postgres` | postgres:16-alpine | business data + model registry |
| `spa-redis` | redis:7-alpine | job queue + cache |

## Full stack

```bash
cp .env.example .env           # set JWT_SECRET, POSTGRES_PASSWORD, etc.
docker compose up --build
# first-time init:
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m app.seed
docker compose exec backend python -m app.seed_phase23
docker compose exec backend python -m ml.data.export_dataset
docker compose exec backend python -m ml.sequences.export_sequences
docker compose exec backend python -m ml.training.train
docker compose exec backend python -m ml.training.train_transformer
docker compose exec backend python -m ml.training.train_hybrid
docker compose exec backend python -m ml.training.compare_models
```

- Frontend: http://localhost:3000 — API docs: http://localhost:8000/docs

## Model artifacts (§59)

Trained models are **not committed to Git** (`.gitignore` excludes `ml/artifacts/*.pt|joblib` and
processed data). The database stores metadata + `artifact_location`; the file/object storage layer
holds the checkpoints. In production, mount a volume or replace `ML_ARTIFACTS_DIR` with an object
store path.

## Production notes

- Put Cloudflare/nginx in front for TLS; set `BACKEND_CORS_ORIGINS` to the real origin.
- Use strong `JWT_SECRET` (≥ 32 bytes, shared with the frontend for middleware verification).
- Scale workers independently of the API (they only need DB + Redis + artifacts).
- Back up PostgreSQL; the model registry is part of the DB.
- Health check: `GET /health`; API schema: `GET /openapi.json`.
