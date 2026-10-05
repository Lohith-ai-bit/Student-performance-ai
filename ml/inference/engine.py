"""Unified inference engine (§18).

    predict(student_id, course_id, model_type, model_version):
        retrieve data -> features -> learning sequence -> load model -> prediction
        -> risk -> save prediction -> trigger explanation -> trigger recommendation

Model type dispatch:
  BASELINE     — Phase 1 sklearn pipelines (joblib artifacts)
  TRANSFORMER  — PyTorch temporal checkpoint
  HYBRID       — PyTorch fusion model (tabular + sequence)

Torch models are loaded lazily and cached per process. Production model
selection comes from the model_versions registry (ModelRegistryService).
"""
import json
import threading
import time
import uuid

import numpy as np
import pandas as pd
import torch

from ml.config import (
    HYBRID_FILE,
    HYBRID_PREPROCESSOR_FILE,
    RISK_SCORE_THRESHOLD,
    TRANSFORMER_FILE,
    TransformerConfig,
)
from ml.models.hybrid import HybridModel
from ml.models.transformer import TransformerPredictor

_lock = threading.Lock()
_torch_cache: dict = {}


def _load_torch(kind: str):
    """Load and cache (model, payload) for TRANSFORMER / HYBRID artifacts."""
    with _lock:
        if kind in _torch_cache:
            return _torch_cache[kind]
        if kind == "TRANSFORMER":
            from ml.config import TRANSFORMER_METADATA_FILE

            if not TRANSFORMER_FILE.exists():
                raise FileNotFoundError("No transformer checkpoint. Run `python -m ml.training.train_transformer`.")
            metadata = json.loads(TRANSFORMER_METADATA_FILE.read_text(encoding="utf-8"))
            config = TransformerConfig.from_dict(metadata["architecture"])
            model = TransformerPredictor(config)
            model.load_state_dict(torch.load(TRANSFORMER_FILE, map_location="cpu"))
            model.eval()
            payload = {"model": model, "metadata": metadata}
        else:
            from ml.config import HYBRID_METADATA_FILE

            if not HYBRID_FILE.exists():
                raise FileNotFoundError("No hybrid checkpoint. Run `python -m ml.training.train_hybrid`.")
            metadata = json.loads(HYBRID_METADATA_FILE.read_text(encoding="utf-8"))
            config = TransformerConfig.from_dict(metadata["architecture"])
            model = HybridModel(n_tabular_features=len(metadata["feature_columns"]), config=config)
            model.load_state_dict(torch.load(HYBRID_FILE, map_location="cpu"))
            model.eval()
            payload = {"model": model, "metadata": metadata}
        _torch_cache[kind] = payload
        return payload


def predict_torch(kind: str, sequences: np.ndarray, masks: np.ndarray, tabular: np.ndarray | None) -> list[dict]:
    """Run a torch model over [N, T, F] standardized inputs; returns per-row outputs."""
    payload = _load_torch(kind)
    model = payload["model"]
    with torch.no_grad():
        seq = torch.from_numpy(sequences.astype(np.float32))
        mask = torch.from_numpy(masks.astype(np.float32))
        if kind == "HYBRID":
            out = model(seq, mask, torch.from_numpy(tabular.astype(np.float32)))
        else:
            out = model(seq, mask)
        return [
            {
                "score_std": float(out["score"][i]),
                "risk_probability": float(torch.sigmoid(out["risk_logit"][i])),
            }
            for i in range(seq.shape[0])
        ]


def denormalize_score(score_std: float, metadata: dict) -> float:
    return score_std * metadata["target_std"] + metadata["target_mean"]


def prepare_inputs(db, student, course_id, kind: str) -> dict:
    """Build model inputs for TRANSFORMER/HYBRID: sequences, masks, pairs, tabular, metadata.

    Shared by the unified engine and the explanation service so both use identical inputs.
    """
    import joblib

    from app.services import feature_service
    from ml.config import SEQUENCE_STATS_FILE
    from ml.sequences.live import build_live_sequence

    sequences, masks, pairs = build_live_sequence(db, student, course_id)
    if len(pairs) == 0:
        return {"sequences": sequences, "masks": masks, "pairs": pairs, "tabular": None, "metadata": None}

    payload = _load_torch(kind)
    metadata = payload["metadata"]
    tabular = None
    if kind == "HYBRID":
        features = feature_service.build_student_feature_frame(db, student, None)
        pre = payload.get("preprocessor")
        if pre is None:
            pre = joblib.load(HYBRID_PREPROCESSOR_FILE)
            _torch_cache["HYBRID"]["preprocessor"] = pre
        feat_by_course = {idx[1]: row for idx, row in features.iterrows()} if not features.empty else {}
        tab = np.zeros((len(pairs), len(metadata["feature_columns"])), dtype=np.float32)
        for i, (sid, cid) in enumerate(pairs):
            row = feat_by_course.get(cid, features.iloc[-1])
            vec = np.array(
                [row[c] if c in row.index else np.nan for c in metadata["feature_columns"]], dtype=np.float32
            )
            tab[i] = pre["tabular_scaler"].transform(vec.reshape(1, -1))[0]
        tabular = tab
    return {
        "sequences": sequences,
        "masks": masks,
        "pairs": pairs,
        "tabular": tabular,
        "metadata": metadata,
    }


def predict(
    db,
    student,
    course_id: uuid.UUID | None,
    model_type: str = "BASELINE",
    model_version: str | None = None,
    persist: bool = True,
    explain: bool = False,
    recommend: bool = False,
    baseline_predictor=None,
) -> dict:
    """Unified prediction entry point (§18). Returns the standard prediction dict."""
    from app.core.errors import NotFoundError, ValidationError
    from app.core.risk_config import classify_risk
    from app.models import Course, Prediction
    from app.models.enums import RiskLevel
    from ml.inference.predictor import PerformancePredictor

    started = time.perf_counter()

    if course_id is not None and db.get(Course, course_id) is None:
        raise NotFoundError("Course could not be found.", code="COURSE_NOT_FOUND")

    model_type = model_type.upper()
    per_course: list[dict] = []
    feature_row = None

    if model_type == "BASELINE":
        predictor = baseline_predictor or PerformancePredictor()
        from app.services import feature_service

        features = feature_service.build_student_feature_frame(db, student, course_id)
        if features.empty:
            raise ValidationError(
                "No assessment, attendance, or learning-activity data is available for this "
                "student yet. Add data and try again.",
                code="INSUFFICIENT_DATA",
            )
        for (sid, cid), row in features.iterrows():
            result = predictor.predict(row.to_frame().T)
            per_course.append(
                {
                    "course_id": cid,
                    "predicted_score": result["predicted_score"],
                    "risk_probability": result["risk_probability"],
                }
            )
        meta_name = predictor.model_name
        meta_version = predictor.model_version
        feature_row = features.iloc[-1]  # most recent course row for explanations
    else:
        inputs = prepare_inputs(db, student, course_id, model_type)
        if inputs["metadata"] is None:
            raise ValidationError(
                "No learning history is available for this student yet. Add data and try again.",
                code="INSUFFICIENT_DATA",
            )
        metadata = inputs["metadata"]
        outputs = predict_torch(model_type, inputs["sequences"], inputs["masks"], inputs["tabular"])
        for (sid, cid), out in zip(inputs["pairs"], outputs):
            per_course.append(
                {
                    "course_id": cid,
                    "predicted_score": round(max(0.0, min(100.0, denormalize_score(out["score_std"], metadata))), 2),
                    "risk_probability": round(max(0.0, min(1.0, out["risk_probability"])), 4),
                }
            )
        meta_name = metadata["model_name"]
        meta_version = metadata["model_version"]
        feature_row = None

    predicted_score = round(
        float(np.mean([p["predicted_score"] for p in per_course if p["predicted_score"] is not None])), 2
    ) if per_course else 0.0
    risk_probability = round(float(np.mean([p["risk_probability"] for p in per_course])), 4) if per_course else 0.0
    risk_level = classify_risk(risk_probability)
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    prediction_row = None
    if persist:
        rows = []
        for p in per_course:
            rows.append(
                Prediction(
                    student_id=student.id,
                    course_id=uuid.UUID(p["course_id"]),
                    model_name=meta_name,
                    model_version=str(meta_version),
                    model_type=model_type,
                    predicted_score=p["predicted_score"],
                    risk_probability=p["risk_probability"],
                    risk_level=RiskLevel(risk_level),
                )
            )
        db.add_all(rows)
        db.commit()
        prediction_row = rows[0] if rows else None

    result = {
        "student_id": str(student.id),
        "course_id": str(course_id) if course_id else None,
        "predicted_score": predicted_score,
        "risk_probability": risk_probability,
        "risk_level": risk_level,
        "model_name": meta_name,
        "model_version": str(meta_version),
        "model_type": model_type,
        "prediction_id": str(prediction_row.id) if prediction_row else "",
        "latency_ms": latency_ms,
        "per_course": per_course,
        "feature_row": feature_row,
    }

    if explain and prediction_row is not None:
        from app.services import explanation_service

        result["explanation"] = explanation_service.generate_for_prediction(db, prediction_row, result, feature_row)

    if recommend and prediction_row is not None:
        from app.services import recommendation_service

        result["recommendations_created"] = recommendation_service.generate_for_prediction(db, student, prediction_row)

    return result
