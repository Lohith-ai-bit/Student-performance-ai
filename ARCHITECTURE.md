# Architecture

```text
                         INTERNET
                            |
                     Cloudflare / reverse proxy
                            |
                  ┌─────────┴─────────┐
                  ↓                   ↓
            Next.js (3000)       (static assets)
                  |
                  | REST (Bearer JWT) via NEXT_PUBLIC_API_URL
                  ↓
            FastAPI (8000)  ← security middleware (rate limit, headers), RBAC
                  |
      ┌───────────┼─────────────────┐
      ↓           ↓                 ↓
 PostgreSQL    Redis          Background worker
 (business     (batch job     python -m app.worker
  data, model   queue +       (batch inference; ML/
  registry,     cache)        transformer/hybrid in
  jobs, audit)                 separate container)
```

## Layers

| Layer | Location | Responsibility |
|---|---|---|
| Frontend | `frontend/` | Next.js App Router, React 19, Tailwind v4, TanStack Query, Recharts |
| API | `backend/app/api/` | FastAPI routes, request validation (Pydantic v2), RBAC |
| Domain services | `backend/app/services/` | business logic (auth, dashboards, explanations, recommendations, ops) |
| Persistence | `backend/app/models/` | SQLAlchemy 2.0 models; Alembic migrations |
| ML | `ml/` | shared feature engineering, sequence pipeline, models, training, inference, explainability |

## Key design decisions

1. **One ML code path for train and serve.** `ml/features/build_features.py` builds the tabular
   feature vector, `ml/sequences/` builds the temporal sequence — used by both the offline
   training CLIs and the FastAPI inference engine, eliminating train/serve skew.
2. **Backend is the authorization boundary.** The Next.js middleware verifies the JWT for
   redirect UX only; every API request is re-checked (RBAC in `app/api/dependencies/auth.py`).
3. **Model registry as source of truth for serving.** The unified inference engine reads
   `model_versions` (status `PRODUCTION`) or falls back to artifact defaults; promotion is an
   explicit admin action (§17, §40).
4. **Long work leaves the request path.** Batch prediction jobs are queued in Redis and executed
   by the worker container; small batches run inline through the same code path.
5. **Explainability and recommendations are pipeline stages of prediction**, not separate
   features — a stored prediction references its SHAP/LIME/gradient factors and its generated
   recommendations.

See also: [ML_ARCHITECTURE.md](ML_ARCHITECTURE.md), [MLOPS.md](MLOPS.md), [DEPLOYMENT.md](DEPLOYMENT.md).
