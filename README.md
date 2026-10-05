# EduPredict — Hybrid ML + Transformer Student Performance Prediction Platform

**A Hybrid Machine Learning–Transformer Framework for Student Performance Prediction and
Personalized Learning Recommendation** — Phases 1–3 (foundation, Transformer/hybrid AI,
explainability, personalization, MLOps).

> ⚠️ All seed data in this repository is **synthetic** — no real student information is used.
> AI predictions are estimates intended to support learning and academic intervention; they never
> replace qualified faculty judgment.

---

## What the system does

```text
Student data → features ─┬─ Traditional ML (Linear/Logistic Regression, RF, XGBoost, LightGBM)
                         └─ Temporal Transformer (PyTorch, weekly learning sequences)
                                      ↓
                              Hybrid fusion (concat | weighted | learned)
                                      ↓
                        Performance prediction + risk classification
                                      ↓
                     Explainable AI (SHAP + LIME + gradient attribution)
                                      ↓
              Personalized recommendations → feedback → progress tracking
                                      ↓
        Model registry · batch prediction · drift monitoring · retraining workflow
```

| Layer | Stack |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, shadcn-style UI, TanStack Query, Recharts |
| API | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, JWT (bcrypt) |
| Data | PostgreSQL 16, Redis 7 |
| ML | scikit-learn, XGBoost, LightGBM, **PyTorch**, **SHAP**, **LIME** |

## Quick start

### Everything in Docker

```bash
cp .env.example .env
docker compose up --build
# one-time init (see DEPLOYMENT.md for the full list):
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m app.seed && docker compose exec backend python -m app.seed_phase23
docker compose exec backend python -m ml.data.export_dataset
docker compose exec backend python -m ml.sequences.export_sequences
docker compose exec backend python -m ml.training.train
docker compose exec backend python -m ml.training.train_transformer
docker compose exec backend python -m ml.training.train_hybrid
```

### Native development

```bash
docker compose up -d postgres redis
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # Windows Git Bash
cp .env.example .env
cd backend && ../.venv/Scripts/python -m alembic upgrade head && ../.venv/Scripts/python -m app.seed
cd .. && .venv/Scripts/python -m ml.data.export_dataset && .venv/Scripts/python -m ml.training.train
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload   # API on :8000
cd ../frontend && npm install && cp .env.example .env.local && npm run dev  # web on :3000
```

### Demo logins (synthetic seed)

| Role | Email | Password |
|---|---|---|
| ADMIN | `admin@university.edu` | `Admin@1234` |
| FACULTY | `faculty1@university.edu` | `Faculty@123` |
| STUDENT | `student1@university.edu` | `Student@123` |

## API surface (prefix `/api/v1`, interactive docs at `/docs`)

**Phase 1 core:** `/auth/*`, `/students/me/*`, `/faculty/*` (student table, data entry, CSV
import), `/admin/*` (students, faculty, departments, courses, enrollments), `/ml/predict`,
`/ml/models`, `/dashboards/*`.

**Phase 2/3 additions:**

```text
POST /ml/predict/advanced | /ml/transformer/predict | /ml/hybrid/predict
GET  /predictions/{id}/explanation            SHAP + LIME + gradient factors, human-readable summary
GET  /students/me/recommendations             personalized plan (weak areas → resources, ranked)
PATCH /recommendations/{id}                   start / complete / dismiss
POST /recommendations/{id}/feedback           rating + helpful flag
GET  /students/me/learning-progress           hours, practice, completion
GET  /students/{id}/recommendations           faculty/admin view
POST /interventions                           faculty decision support (§34)
GET  /resources                               searchable catalogue
GET  /ml/registry (+sync, /{id}/promote)      model registry, only VALIDATED → PRODUCTION
GET  /ml/experiments                          real experiment results (comparison + ablations)
POST /ml/batch-predictions                    student/course/class/department (queue or inline)
GET  /admin/monitoring | /admin/drift         prediction health, latency, PSI drift
```

## Research results (synthetic dataset — actual runs, see MODEL_EVALUATION.md)

| Model (test split) | RMSE ↓ | R² | F1 ↑ | ROC-AUC |
|---|---|---|---|---|
| LinearRegression | **9.41** | **0.839** | 0.818 | 0.960 |
| Transformer only | 15.09 | 0.587 | 0.792 | 0.919 |
| **Hybrid (learned fusion)** | 9.86 | 0.824 | **0.844** | 0.953 |

The hybrid beats the transformer-only model and the tree ensembles and is the best risk
classifier, but does not out-perform LinearRegression on RMSE for this small synthetic dataset —
reported honestly rather than claimed generally. Ablations (−attendance, −behaviour,
−historical) each degrade performance.

## Documentation

[ARCHITECTURE.md](ARCHITECTURE.md) · [ML_ARCHITECTURE.md](ML_ARCHITECTURE.md) ·
[TRANSFORMER.md](TRANSFORMER.md) · [HYBRID_MODEL.md](HYBRID_MODEL.md) ·
[EXPLAINABILITY.md](EXPLAINABILITY.md) · [RECOMMENDATION_ENGINE.md](RECOMMENDATION_ENGINE.md) ·
[MODEL_EVALUATION.md](MODEL_EVALUATION.md) · [MLOPS.md](MLOPS.md) · [DEPLOYMENT.md](DEPLOYMENT.md)

## Tests

```bash
cd backend && ../.venv/Scripts/python -m pytest tests -q      # 41 tests: auth, DB, ML, API, sequences,
                                                              # transformer, hybrid, explainability, RBAC
.venv/Scripts/python scripts/verify_api.py                    # 38 live checks (Phase 1)
.venv/Scripts/python scripts/verify_phase23.py                # 33 live checks (advanced system)
```

## Known limitations

- Dashboard aggregates computed in pandas (capstone scale); move to SQL when data grows.
- Baselines trained without id columns; predictions carry model_type since the advanced migration.
- Metrics reflect a small synthetic dataset (480 training rows) and will change with real data.
- `middleware.ts` is deprecated in Next 16 (renameable to `proxy.ts` via codemod).
- Recommendations are rule-based with configurable ranking; a learned recommender and a causal
  evaluation of impact are future work.
