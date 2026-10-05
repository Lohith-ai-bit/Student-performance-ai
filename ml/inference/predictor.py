"""Inference: load trained artifacts and predict for one (student, course) feature row."""
import json
import math
from pathlib import Path

import joblib
import pandas as pd

from ml.config import (
    METADATA_FILE,
    MODEL_CLASSIFICATION_FILE,
    MODEL_REGRESSION_FILE,
    RISK_SCORE_THRESHOLD,
)
from ml.features.build_features import FEATURE_COLUMNS


def _risk_probability_from_score(score: float, threshold: float = RISK_SCORE_THRESHOLD) -> float:
    """Fallback when no classifier artifact exists: smooth logistic mapping of score -> P(risk)."""
    steepness = 8.0
    return 1.0 / (1.0 + math.exp((score - threshold) / steepness))


class PerformancePredictor:
    def __init__(self, artifacts_dir: Path | None = None):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else METADATA_FILE.parent
        self.metadata: dict = {}
        self.regression = None
        self.classification = None
        if METADATA_FILE.exists():
            self.metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        if MODEL_REGRESSION_FILE.exists():
            self.regression = joblib.load(MODEL_REGRESSION_FILE)
        if MODEL_CLASSIFICATION_FILE.exists():
            self.classification = joblib.load(MODEL_CLASSIFICATION_FILE)
        if self.regression is None and self.classification is None:
            raise FileNotFoundError(
                f"No trained model artifacts found in {self.artifacts_dir}. "
                "Run `python -m ml.training.train` first."
            )

    # ------------------------------------------------------------------ metadata
    @property
    def model_name(self) -> str:
        return self.metadata.get("models", {}).get("regression", {}).get("model_name", "unknown")

    @property
    def model_version(self) -> str:
        return self.metadata.get("models", {}).get("regression", {}).get("model_version", "unknown")

    def info(self) -> dict:
        models = self.metadata.get("models", {})
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "trained_at": self.metadata.get("trained_at"),
            "dataset_version": self.metadata.get("dataset_version"),
            "feature_version": self.metadata.get("feature_version"),
            "regression": models.get("regression"),
            "classification": models.get("classification"),
        }

    # ------------------------------------------------------------------ predict
    def predict(self, features: pd.DataFrame) -> dict:
        """`features`: one-row DataFrame containing FEATURE_COLUMNS."""
        row = features.iloc[[0]][FEATURE_COLUMNS]

        predicted_score: float | None = None
        risk_probability: float | None = None

        if self.regression is not None:
            predicted_score = float(self.regression.predict(row)[0])
            predicted_score = max(0.0, min(100.0, predicted_score))

        if self.classification is not None and hasattr(self.classification, "predict_proba"):
            risk_probability = float(self.classification.predict_proba(row)[0][1])
        elif predicted_score is not None:
            risk_probability = _risk_probability_from_score(predicted_score)
        else:
            raise RuntimeError("No usable model artifact for prediction.")

        return {
            "predicted_score": round(predicted_score, 2) if predicted_score is not None else None,
            "risk_probability": round(max(0.0, min(1.0, risk_probability)), 4),
        }
