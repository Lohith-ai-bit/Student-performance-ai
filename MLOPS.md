# MLOps

## Model registry (§17)

`model_versions` stores every trainable artifact's identity: name, type (BASELINE / TRANSFORMER /
HYBRID), version, dataset + feature versions, metrics, hyperparameters, artifact location and
status. Lifecycle:

```text
TRAINING → VALIDATED → PRODUCTION → ARCHIVED
                ↘ FAILED
```

- `POST /api/v1/ml/registry/sync` (admin) — registers models found in `ml/artifacts/*metadata.json`
- `POST /api/v1/ml/registry/{id}/promote` (admin) — VALIDATED → PRODUCTION; demotes the previous
  production model of the same type. Only validated models can be promoted (§17).
- The unified inference engine serves the PRODUCTION model of the requested type.

## Batch prediction (§41/§42)

```text
POST /api/v1/ml/batch-predictions  {scope: STUDENT|COURSE|CLASS|DEPARTMENT}
      ↓
small (≤50) → executed inline via the same code path
large       → job queued in Redis ("spa:batch_jobs")
      ↓
worker container (python -m app.worker) pops jobs and predicts student-by-student,
updating progress in batch_prediction_jobs
```

`GET /api/v1/ml/batch-predictions/{job_id}` exposes status, processed/failed counts and results.

## Monitoring (§38) — `/admin/monitoring`

- Prediction counts by model type, risk distribution
- Failed batch jobs
- Inference latency (recent average + p95, recorded per prediction request)

## Data & feature drift (§39) — `/admin/drift`

Population Stability Index (PSI) per monitored feature between the training dataset snapshot
(`ml/data/processed/dataset.csv`) and the current live feature distributions:

- PSI < 0.10 → NORMAL, < 0.25 → WARNING, else DRIFT DETECTED

**Drift is informational.** It never triggers automatic model replacement (§39).

## Retraining workflow (§40)

```text
New data → python -m ml.data.export_dataset && python -m ml.sequences.export_sequences
        → python -m ml.training.train / train_transformer / train_hybrid
        → evaluation vs the production model (experiment report)
        → registry sync (new version = VALIDATED)
        → explicit admin promotion to PRODUCTION
```

A newly trained model is never deployed automatically (§40).

## CI/CD (§60)

`.github/workflows/ci.yml`: ruff lint → compileall type sanity → backend/ML pytest → frontend
build (TypeScript + ESLint) → Docker image builds on main. Deployment is blocked when critical
tests fail.

## Responsible AI (§49)

Every prediction surface carries the disclaimer; risk probabilities are labeled as estimates;
no academic decision is automated; sensitive attributes (gender, ethnicity, income, disability)
are not collected or used.
