"""Model registry endpoints' backing service: reads artifact metadata (§28/§29).

All metrics surfaced here come from actual training experiments — nothing is
fabricated. If no artifacts exist yet, the API reports an empty registry.
"""
import json
from pathlib import Path

import pandas as pd

from app.core.config import settings


def _artifacts_dir() -> Path:
    return Path(settings.ML_ARTIFACTS_DIR)


def get_metadata() -> dict | None:
    metadata_file = _artifacts_dir() / "metadata.json"
    if not metadata_file.exists():
        return None
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def list_models() -> list[dict]:
    metadata = get_metadata()
    if not metadata:
        return []
    models = []
    for task in ("regression", "classification"):
        info = metadata.get("models", {}).get(task)
        if not info:
            continue
        models.append(
            {
                "model_name": info["model_name"],
                "model_version": info["model_version"],
                "task": task,
                "trained_at": metadata.get("trained_at"),
                "dataset_version": metadata.get("dataset_version"),
                "feature_version": metadata.get("feature_version"),
                "metrics": {"validation": info.get("validation_metrics"), "test": info.get("test_metrics")},
                "selected": True,
            }
        )
    return models


def list_evaluations() -> list[dict]:
    """Every trained model's validation metrics from the experiment tables."""
    evaluations: list[dict] = []
    metadata = get_metadata()
    if not metadata:
        return evaluations
    for task in ("regression", "classification"):
        info = metadata.get("models", {}).get(task, {})
        for row in info.get("all_validation_results", []):
            evaluations.append({"model_name": row["model_name"], "task": task, "metrics": row["validation"]})
    return evaluations
