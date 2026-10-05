"""Model monitoring + data drift (§38/§39).

Drift: Population Stability Index (PSI) between the TRAINING dataset snapshot and
the current live feature distributions. PSI < 0.1 NORMAL, < 0.25 WARNING, else
DRIFT DETECTED. Drift never triggers automatic model replacement (§39).
"""
import json
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings

# recent inference latencies (in-process ring buffer; durable latency lives in audit logs)
_LATENCIES: deque = deque(maxlen=500)

MONITORED_FEATURES = [
    "attendance_percentage",
    "quiz_average",
    "assignment_average",
    "midterm_score",
    "engagement_score",
    "session_hours_per_week",
]

PSI_NORMAL = 0.10
PSI_WARNING = 0.25
PSI_BINS = 10


def record_latency(ms: float) -> None:
    _LATENCIES.append(ms)


def latency_stats() -> dict:
    if not _LATENCIES:
        return {"count": 0, "avg_ms": None, "p95_ms": None}
    arr = np.array(_LATENCIES)
    return {
        "count": int(len(arr)),
        "avg_ms": round(float(arr.mean()), 1),
        "p95_ms": round(float(np.percentile(arr, 95)), 1),
    }


def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = PSI_BINS) -> float:
    """Population Stability Index between two samples."""
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) < 10 or len(actual) < 10:
        return 0.0
    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.percentile(expected, quantiles)
    edges[0], edges[-1] = -np.inf, np.inf
    e_counts = np.histogram(expected, bins=edges)[0] / max(1, len(expected))
    a_counts = np.histogram(actual, bins=edges)[0] / max(1, len(actual))
    e_counts = np.clip(e_counts, 1e-6, None)
    a_counts = np.clip(a_counts, 1e-6, None)
    return float(np.sum((a_counts - e_counts) * np.log(a_counts / e_counts)))


def _training_reference() -> pd.DataFrame | None:
    dataset_file = Path(settings.ML_ARTIFACTS_DIR).parent / "data" / "processed" / "dataset.csv"
    if not dataset_file.exists():
        return None
    return pd.read_csv(dataset_file)


def drift_report(db: Session) -> dict:
    """Compare training vs live feature distributions."""
    from app.services.feature_service import build_student_feature_frame
    from app.models import Student

    reference = _training_reference()
    if reference is None:
        return {"status": "NO_REFERENCE", "features": [], "message": "Training dataset snapshot not found."}

    students = db.query(Student).limit(80).all()
    live_frames = []
    for student in students:
        try:
            frame = build_student_feature_frame(db, student, None)
            if not frame.empty:
                live_frames.append(frame.reset_index())
        except Exception:
            continue

    features: list[dict] = []
    worst_psi = 0.0
    if live_frames:
        live = pd.concat(live_frames, ignore_index=True)
        for feature in MONITORED_FEATURES:
            if feature not in reference.columns or feature not in live.columns:
                continue
            psi = _psi(
                reference[feature].to_numpy(dtype=float),
                live[feature].to_numpy(dtype=float),
            )
            status = "NORMAL" if psi < PSI_NORMAL else ("WARNING" if psi < PSI_WARNING else "DRIFT DETECTED")
            worst_psi = max(worst_psi, psi)
            features.append(
                {
                    "feature": feature,
                    "psi": round(psi, 4),
                    "status": status,
                    "training_mean": round(float(reference[feature].mean()), 2) if not reference[feature].isna().all() else None,
                    "live_mean": round(float(live[feature].mean()), 2) if not live[feature].isna().all() else None,
                }
            )

    overall = "NORMAL" if worst_psi < PSI_NORMAL else ("WARNING" if worst_psi < PSI_WARNING else "DRIFT DETECTED")
    return {
        "status": overall,
        "features": features,
        "latency": latency_stats(),
        "message": (
            "Drift status is informational — it never triggers automatic model replacement. "
            "Retraining requires explicit approval."
        ),
    }


def monitoring_summary(db: Session) -> dict:
    """Model performance + prediction distribution + failed predictions (§38)."""
    from sqlalchemy import func

    from app.models import BatchPredictionJob, Prediction

    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0
    avg_score = db.query(func.avg(Prediction.predicted_score)).scalar()
    by_type = dict(
        db.query(Prediction.model_type, func.count(Prediction.id)).group_by(Prediction.model_type).all()
    )
    risk_counts = dict(
        db.query(Prediction.risk_level, func.count(Prediction.id)).group_by(Prediction.risk_level).all()
    )
    failed_jobs = (
        db.query(func.count(BatchPredictionJob.id)).filter(BatchPredictionJob.status == "FAILED").scalar() or 0
    )

    return {
        "total_predictions": int(total_predictions),
        "average_predicted_score": round(float(avg_score), 2) if avg_score is not None else None,
        "predictions_by_model_type": {k.value if hasattr(k, "value") else k: int(v) for k, v in by_type.items()},
        "risk_distribution": {k.value if hasattr(k, "value") else k: int(v) for k, v in risk_counts.items()},
        "failed_batch_jobs": int(failed_jobs),
        "latency": latency_stats(),
    }
