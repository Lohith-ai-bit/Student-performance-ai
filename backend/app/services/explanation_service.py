"""Explanation service (§21/§22): SHAP + LIME for tabular components, gradient
attributions for the Transformer; human-readable summaries; persisted per prediction."""
import uuid

import numpy as np

from sqlalchemy.orm import Session

from app.models import Prediction, PredictionExplanation
from app.models.advanced_enums import ExplanationMethod

# background/tabular sample cache per process (SHAP background + LIME training data)
_cache: dict = {}


def _tabular_background(feature_columns: list[str], sample_rows: int = 40) -> "object":
    """Sample of training dataset rows used as SHAP background / LIME training data."""
    key = tuple(feature_columns)
    if key in _cache:
        return _cache[key]
    import pandas as pd

    from ml.config import DATASET_FILE

    if not DATASET_FILE.exists():
        raise FileNotFoundError("Training dataset not found; run `python -m ml.data.export_dataset` first.")
    df = pd.read_csv(DATASET_FILE)
    cols = [c for c in feature_columns if c in df.columns]
    background = df[cols].head(sample_rows * 5).copy()
    # fill sparse features (median first, 0 for all-NaN columns) so the background has no NaNs
    background = background.fillna(background.median(numeric_only=True)).fillna(0.0)
    background = background.head(sample_rows).reset_index(drop=True)
    _cache[key] = background
    return background


def generate_for_prediction(db: Session, prediction: Prediction, result: dict, feature_row=None) -> dict:
    """Compute + persist explanations for a stored prediction. Returns the API payload."""
    factors_by_method: dict[str, list[dict]] = {}
    summary = ""

    if result.get("model_type") in ("BASELINE", None, "") or result.get("model_type") == "BASELINE":
        # tabular component -> SHAP + LIME over the numeric feature columns,
        # with categorical columns held at the served row's values
        from ml.explainability.lime_explainer import LimeTabularExplainer
        from ml.explainability.shap_explainer import ShapTabularExplainer
        from ml.features.build_features import FEATURE_COLUMNS, FEATURE_COLUMNS_CATEGORICAL, FEATURE_COLUMNS_NUMERIC
        from ml.inference.predictor import PerformancePredictor

        predictor = PerformancePredictor()
        pipeline = predictor.regression
        if feature_row is None:
            feature_row = result.get("feature_row")
        if feature_row is None:
            raise ValueError("No feature row available for explanation")

        base_row = feature_row[FEATURE_COLUMNS]
        categorical_values = {c: base_row[c] for c in FEATURE_COLUMNS_CATEGORICAL}

        def _augment(numeric_data) -> "object":
            """KernelExplainer/LIME pass numpy arrays — normalize to a full feature DataFrame."""
            import pandas as pd

            if isinstance(numeric_data, pd.DataFrame):
                full = numeric_data.copy()
            else:
                full = pd.DataFrame(np.asarray(numeric_data), columns=FEATURE_COLUMNS_NUMERIC)
            for col, value in categorical_values.items():
                full[col] = value
            return full[FEATURE_COLUMNS]

        background = _tabular_background(FEATURE_COLUMNS_NUMERIC)
        X = base_row[FEATURE_COLUMNS_NUMERIC].to_frame().T
        # live rows carry NaN for sparse features; fill with the background medians (same as background)
        X = X.fillna(background.median(numeric_only=True)).fillna(0.0)

        shap_explainer = ShapTabularExplainer(
            lambda numeric_df: pipeline.predict(_augment(numeric_df)), background, FEATURE_COLUMNS_NUMERIC
        )
        factors_by_method["SHAP"] = shap_explainer.local(X, max_features=6)
        lime = LimeTabularExplainer(background, FEATURE_COLUMNS_NUMERIC, mode="regression")
        factors_by_method["LIME"] = lime.local(
            lambda numeric_df: pipeline.predict(_augment(numeric_df)), X, num_features=6
        )
        summary = shap_explainer.summarize(factors_by_method["SHAP"], result["predicted_score"], result["risk_level"])
    else:
        # Transformer/Hybrid: gradient x input attribution over the sequence
        import torch as _torch

        from ml.explainability.gradient import gradient_attribution
        from ml.inference.engine import prepare_inputs

        inputs = prepare_inputs(db, _student_of(db, prediction), None, result["model_type"])
        if inputs["metadata"] is not None:
            payload = _load_torch_for(result["model_type"])
            model = payload["model"]
            tabular = inputs["tabular"]
            factors = gradient_attribution(
                model,
                _torch.from_numpy(inputs["sequences"][-1:]),
                _torch.from_numpy(inputs["masks"][-1:]),
                output="score",
                max_features=6,
                tabular=_torch.from_numpy(tabular[-1:]) if tabular is not None else None,
            )
            method = "GRADIENT"
            factors_by_method[method] = factors
            positives = [f["label"] for f in factors if f["direction"] == "positive"][:3]
            negatives = [f["label"] for f in factors if f["direction"] == "negative"][:3]
            summary = (
                f"The model estimates a predicted final score of about {result['predicted_score']:.0f}% "
                f"with a {result['risk_level'].lower()} risk level, based on the student's recent "
                "learning timeline."
            )
            if negatives:
                summary += " Recent patterns contributing downward pressure: " + ", ".join(negatives) + "."
            if positives:
                summary += " Patterns working in the student's favour: " + ", ".join(positives) + "."
            summary += (
                " This is an AI-generated estimate intended to support learning and academic "
                "intervention — it is not a definitive judgment of student ability."
            )

    # persist
    db.query(PredictionExplanation).filter(PredictionExplanation.prediction_id == prediction.id).delete()
    for method_str, factors in factors_by_method.items():
        for f in factors:
            db.add(
                PredictionExplanation(
                    prediction_id=prediction.id,
                    method=method_str,
                    feature=f["feature"],
                    importance=float(f["importance"]),
                    direction=f["direction"],
                    explanation_text=f.get("explanation_text", ""),
                )
            )
    db.commit()

    return {
        "prediction": {
            "id": str(prediction.id),
            "predicted_score": prediction.predicted_score,
            "risk_probability": prediction.risk_probability,
            "risk_level": prediction.risk_level.value if hasattr(prediction.risk_level, "value") else str(prediction.risk_level),
            "model_name": prediction.model_name,
            "model_version": prediction.model_version,
            "model_type": prediction.model_type,
        },
        "shap": factors_by_method.get("SHAP", []),
        "lime": factors_by_method.get("LIME", []),
        "gradient": factors_by_method.get("GRADIENT", []),
        "summary": summary,
        "factors": (factors_by_method.get("SHAP") or factors_by_method.get("GRADIENT") or [])[:6],
        "disclaimer": (
            "This prediction is an AI-generated estimate intended to support learning and "
            "academic intervention. It should not be treated as a definitive judgment of student ability."
        ),
    }


def _student_of(db: Session, prediction: Prediction):
    from app.models import Student

    return db.get(Student, prediction.student_id)


def _load_torch_for(model_type: str):
    from ml.inference.engine import _load_torch

    return _load_torch(model_type)


def get_explanation(db: Session, prediction_id: uuid.UUID) -> dict | None:
    prediction = db.get(Prediction, prediction_id)
    if prediction is None:
        return None
    rows = (
        db.query(PredictionExplanation)
        .filter(PredictionExplanation.prediction_id == prediction_id)
        .all()
    )
    shap_rows = [_factor(r) for r in rows if r.method == ExplanationMethod.SHAP.value or r.method == "SHAP"]
    lime_rows = [_factor(r) for r in rows if r.method == ExplanationMethod.LIME.value or r.method == "LIME"]
    gradient_rows = [_factor(r) for r in rows if r.method == "GRADIENT"]
    factors = shap_rows or gradient_rows or lime_rows

    # summary is reconstructed from the stored factors (supportive, non-judgmental framing)
    if factors:
        positives = [f["label"] for f in factors if f["direction"] == "positive"][:3]
        negatives = [f["label"] for f in factors if f["direction"] == "negative"][:3]
        risk_level = (
            prediction.risk_level.value if hasattr(prediction.risk_level, "value") else str(prediction.risk_level)
        )
        parts = [
            f"The model estimates a predicted final score of about {prediction.predicted_score:.0f}% "
            f"with a {str(risk_level).lower()} risk level."
        ]
        if negatives:
            parts.append("This estimate is influenced downward mainly by " + ", ".join(negatives) + ".")
        if positives:
            parts.append("Working in the student's favour: " + ", ".join(positives) + ".")
        parts.append(
            "This is an AI-generated estimate intended to support learning and academic "
            "intervention — it is not a definitive judgment of student ability."
        )
        summary = " ".join(parts)

    return {
        "prediction": prediction,
        "shap": shap_rows,
        "lime": lime_rows,
        "gradient": gradient_rows,
        "summary": summary,
        "factors": factors[:6],
        "disclaimer": (
            "This prediction is an AI-generated estimate intended to support learning and "
            "academic intervention. It should not be treated as a definitive judgment of student ability."
        ),
    }


def _factor(row: PredictionExplanation) -> dict:
    return {
        "feature": row.feature,
        "label": row.feature.replace("_", " ").title(),
        "importance": row.importance,
        "direction": row.direction,
        "explanation_text": row.explanation_text,
    }
