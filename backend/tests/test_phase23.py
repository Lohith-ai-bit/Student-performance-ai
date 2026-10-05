"""Phase 2/3 tests: sequence pipeline, Transformer, Hybrid, explainability,
recommendations, and advanced API flows."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.config import SEQUENCE_FEATURES, TransformerConfig  # noqa: E402


# ------------------------------------------------------------------ sequences
def test_sequence_builder_chronological_and_masked():
    from ml.sequences.sequence_builder import build_weekly_sequence

    assessments = pd.DataFrame(
        [
            {"student_id": "S1", "course_id": "C1", "assessment_type": "QUIZ", "score": 80, "maximum_score": 100, "assessment_date": "2026-01-10"},
            {"student_id": "S1", "course_id": "C1", "assessment_type": "QUIZ", "score": 60, "maximum_score": 100, "assessment_date": "2026-01-24"},
        ]
    )
    activities = pd.DataFrame(
        [
            {"student_id": "S1", "course_id": "C1", "activity_date": "2026-01-12", "session_duration": 60, "videos_watched": 4, "videos_completed": 3, "documents_opened": 1, "quiz_attempts": 1, "assignments_submitted": 1, "late_submissions": 0, "practice_questions_attempted": 10, "login_count": 4},
            {"student_id": "S1", "course_id": "C1", "activity_date": "2026-01-26", "session_duration": 30, "videos_watched": 2, "videos_completed": 0, "documents_opened": 0, "quiz_attempts": 0, "assignments_submitted": 0, "late_submissions": 0, "practice_questions_attempted": 0, "login_count": 1},
        ]
    )
    seq, mask = build_weekly_sequence(assessments, pd.DataFrame(), activities, "S1", "C1", pd.Timestamp("2026-02-01"))
    assert seq.shape[1] == len(SEQUENCE_FEATURES)
    # quiz_average in the last week with a quiz = 60
    quiz_col = SEQUENCE_FEATURES.index("quiz_average")
    last_masked = mask == 1
    assert seq[last_masked][-1][quiz_col] == pytest.approx(60.0, abs=0.5)
    # chronological ordering with observed weeks marked
    assert mask.sum() >= 2 and mask[-1] == 1.0
    # quiz average carried forward: the LAST observed week holds the newest quiz (60)
    assert seq[mask == 1][-1][quiz_col] <= seq[mask == 1][0][quiz_col] + 1e-3


def test_collator_pads_left_and_builds_masks():
    import torch

    from ml.sequences.collator import SequenceCollator

    batch = [
        {"sequence": torch.ones(3, 5), "mask": torch.ones(3), "tabular": torch.zeros(2), "y_regression": torch.tensor(1.0), "y_classification": torch.tensor(0.0)},
        {"sequence": torch.ones(5, 5), "mask": torch.ones(5), "tabular": torch.zeros(2), "y_regression": torch.tensor(2.0), "y_classification": torch.tensor(1.0)},
    ]
    out = SequenceCollator(max_length=5)(batch)
    assert out["sequence"].shape == (2, 5, 5)
    assert out["src_key_padding_mask"][0][:2].all()   # first 2 steps padded
    assert not out["src_key_padding_mask"][0][2:].any()


# ----------------------------------------------------------------- transformer
def test_transformer_forward_and_checkpoint_roundtrip(tmp_path):
    import torch

    from ml.models.transformer import TransformerPredictor

    config = TransformerConfig(sequence_length=6, n_features=len(SEQUENCE_FEATURES), embedding_dimension=16, encoder_layers=1, feedforward_dimension=16)
    model = TransformerPredictor(config)
    seq = torch.randn(2, 6, len(SEQUENCE_FEATURES))
    mask = torch.ones(2, 6)
    model.eval()
    out = model(seq, mask)
    assert out["score"].shape == (2,)
    assert out["risk_logit"].shape == (2,)
    assert out["representation"].shape == (2, 16)

    # checkpoint round-trip
    path = tmp_path / "model.pt"
    torch.save(model.state_dict(), path)
    model2 = TransformerPredictor(config)
    model2.load_state_dict(torch.load(path, map_location="cpu"))
    model2.eval()
    out2 = model2(seq, mask)
    assert torch.allclose(out["score"], out2["score"], atol=1e-5)


def test_hybrid_fusion_variants_forward():
    import torch

    from ml.models.hybrid import HybridModel

    config = TransformerConfig(sequence_length=4, n_features=len(SEQUENCE_FEATURES), embedding_dimension=16, encoder_layers=1, feedforward_dimension=16)
    for fusion in ("concat", "weighted", "learned"):
        config.fusion = fusion
        model = HybridModel(n_tabular_features=7, config=config)
        out = model(torch.randn(3, 4, len(SEQUENCE_FEATURES)), torch.ones(3, 4), torch.randn(3, 7))
        assert out["score"].shape == (3,)
        assert not torch.isnan(out["score"]).any()


def test_gradient_attribution_for_hybrid():
    import torch

    from ml.explainability.gradient import gradient_attribution
    from ml.models.hybrid import HybridModel

    config = TransformerConfig(sequence_length=4, n_features=len(SEQUENCE_FEATURES), embedding_dimension=16, encoder_layers=1, feedforward_dimension=16)
    model = HybridModel(n_tabular_features=5, config=config)
    factors = gradient_attribution(
        model, torch.randn(1, 4, len(SEQUENCE_FEATURES)), torch.ones(1, 4),
        output="score", tabular=torch.randn(1, 5),
    )
    assert 0 < len(factors) <= 6
    assert all("label" in f and "importance" in f for f in factors)


# --------------------------------------------------------------- explainability
def test_shap_and_lime_on_tiny_pipeline():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    from ml.explainability.lime_explainer import LimeTabularExplainer
    from ml.explainability.shap_explainer import ShapTabularExplainer

    rng = np.random.default_rng(7)
    cols = ["quiz_average", "attendance_percentage"]
    X = pd.DataFrame({"quiz_average": rng.uniform(30, 100, 60), "attendance_percentage": rng.uniform(40, 100, 60)})
    y = X["quiz_average"] * 0.6 + X["attendance_percentage"] * 0.4
    pipe = Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", LinearRegression())]).fit(X, y)

    shap_explainer = ShapTabularExplainer(lambda df_: pipe.predict(df_), X, cols)
    row = X.iloc[[0]]
    factors = shap_explainer.local(row, max_features=2)
    assert len(factors) == 2
    assert all(f["direction"] in ("positive", "negative") for f in factors)
    summary = shap_explainer.summarize(factors, float(pipe.predict(row)[0]), "LOW")
    assert "AI-generated estimate" in summary

    lime = LimeTabularExplainer(X, cols, mode="regression")
    lime_factors = lime.local(lambda df_: pipe.predict(df_), row, num_features=2)
    assert len(lime_factors) == 2


# ------------------------------------------------------------- recommendation
def test_recommendation_flow_full(client, auth_faculty, auth_student, seed_users, add_student_records):
    """End-to-end §55: predict -> explanation -> recommendation -> complete -> feedback."""
    student = add_student_records["student"]
    prof = client.get("/api/v1/students/me", headers=auth_student).json()

    # advanced prediction with explanation + recommendations
    r = client.post(
        "/api/v1/ml/predict/advanced",
        headers=auth_student,
        json={"student_id": prof["id"], "course_id": None, "explain": True, "recommend": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["explanation"] is not None
    assert body["recommendations_created"] >= 0

    recs = client.get("/api/v1/students/me/recommendations", headers=auth_student).json()
    if recs:
        rec = recs[0]
        r = client.patch(f"/api/v1/recommendations/{rec['id']}", headers=auth_student, json={"status": "COMPLETED"})
        assert r.status_code == 200
        r = client.post(
            f"/api/v1/recommendations/{rec['id']}/feedback",
            headers=auth_student,
            json={"rating": 5, "helpful": True},
        )
        assert r.status_code == 200

    progress = client.get("/api/v1/students/me/learning-progress", headers=auth_student).json()
    assert progress["learning_hours"] >= 0

    # intervention (§34)
    r = client.post(
        "/api/v1/interventions",
        headers=auth_faculty,
        json={"student_id": str(student.id), "note": "Additional academic support recommended.", "intervention_type": "EXTRA_TUTORING"},
    )
    assert r.status_code == 200

    # notifications generated for the student (§43)
    notes = client.get("/api/v1/notifications", headers=auth_student).json()
    assert isinstance(notes, list)


def test_weak_area_detection_rules(db_session, seed_users, add_student_records):
    from app.models import Prediction
    from app.services.recommendation_service import detect_weak_areas

    student = add_student_records["student"]
    # low predicted score + high risk probability -> weak areas should be found
    prediction = Prediction(
        student_id=student.id, course_id=seed_users["course"].id, model_name="test", model_version="1.0",
        model_type="BASELINE", predicted_score=40.0, risk_probability=0.8, risk_level="HIGH",
    )
    db_session.add(prediction)
    db_session.commit()

    areas = detect_weak_areas(db_session, student, prediction)
    kinds = {a.kind for a in areas}
    assert "assessment_type" in kinds or "course" in kinds
    assert all(0.0 <= a.severity <= 1.0 for a in areas)


# --------------------------------------------------------------------- RBAC
def test_advanced_rbac(client, auth_student, auth_faculty, seed_users):
    r = client.get("/api/v1/admin/monitoring", headers=auth_student)
    assert r.status_code == 403
    r = client.post("/api/v1/ml/registry/sync", headers=auth_faculty)
    assert r.status_code == 403
    r = client.get("/api/v1/ml/experiments", headers=auth_student)
    assert r.status_code == 200
