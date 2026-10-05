"""SHAP explanations for the tabular/ML component (§19).

Provides global importance (over a background sample) and local (per-prediction)
importance with positive/negative factors, converted into human-readable text.
"""
import numpy as np
import pandas as pd

from ml.explainability.labels import describe_factor, label_for


class ShapTabularExplainer:
    """Wraps a predict_fn(X) -> float array with SHAP and explains single rows."""

    def __init__(self, predict_fn, background: pd.DataFrame, feature_names: list[str], seed: int = 42):
        import shap

        self.predict_fn = predict_fn
        self.feature_names = feature_names
        self.background = background.reset_index(drop=True)
        self.explainer = shap.KernelExplainer(predict_fn, self.background.iloc[: min(25, len(background))], seed=seed)

    def local(self, features: pd.DataFrame, max_features: int = 8) -> list[dict]:
        """Per-feature attribution for one row (positive + negative factors)."""
        values = np.array(self.explainer.shap_values(features, silent=True))
        if isinstance(values, list):  # multi-output explainers
            values = values[0]
        values = np.asarray(values).reshape(-1)[: len(self.feature_names)]
        order = np.argsort(-np.abs(values))[:max_features]

        factors = []
        for idx in order:
            importance = float(values[idx])
            factors.append(
                {
                    "feature": self.feature_names[idx],
                    "label": label_for(self.feature_names[idx]),
                    "importance": round(importance, 4),
                    "direction": "positive" if importance >= 0 else "negative",
                }
            )
        for f in factors:
            f["explanation_text"] = describe_factor(f["label"], f["importance"], f["direction"])
        return factors

    def global_importance(self, sample: pd.DataFrame | None = None, max_features: int = 12) -> list[dict]:
        """Mean |SHAP| over a background/sample set — the model's global factors."""
        data = (sample or self.background).reset_index(drop=True)
        values = np.array(self.explainer.shap_values(data, silent=True))
        if isinstance(values, list):
            values = values[0]
        values = np.asarray(values)
        if values.ndim == 3:  # [samples, features, outputs]
            values = values[..., 0]
        mean_abs = np.abs(values).mean(axis=0).reshape(-1)[: len(self.feature_names)]
        order = np.argsort(-mean_abs)[:max_features]
        return [
            {"feature": self.feature_names[i], "label": label_for(self.feature_names[i]), "importance": round(float(mean_abs[i]), 4)}
            for i in order
        ]

    def summarize(self, local_factors: list[dict], predicted_score: float, risk_level: str) -> str:
        """Human-readable summary (§21) — supportive, never a verdict."""
        positives = [f["label"] for f in local_factors if f["direction"] == "positive"][:3]
        negatives = [f["label"] for f in local_factors if f["direction"] == "negative"][:3]
        parts = [
            f"The model estimates a predicted final score of about {predicted_score:.0f}% "
            f"with a {risk_level.lower()} risk level."
        ]
        if negatives:
            parts.append(
                "This estimate is influenced downward mainly by " + ", ".join(negatives) + "."
            )
        if positives:
            parts.append("Working in the student's favour: " + ", ".join(positives) + ".")
        parts.append(
            "This is an AI-generated estimate intended to support learning and academic "
            "intervention — it is not a definitive judgment of student ability."
        )
        return " ".join(parts)
