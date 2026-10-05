"""ML tests (§39): preprocessing/feature engineering, model loading, prediction, risk calculation."""
import numpy as np
import pandas as pd
import pytest

from ml.features.build_features import FEATURE_COLUMNS, TARGET_COLUMN, build_features, build_training_dataset
from ml.features.engagement import ENGAGEMENT_WEIGHTS, compute_engagement_score
from ml.inference.predictor import _risk_probability_from_score
from app.core.risk_config import classify_risk, get_risk_thresholds


def _raw_frames():
    students = pd.DataFrame(
        [{"id": "S1", "department": "CSE", "branch": "CS", "year": 2, "semester": 3, "section": "A", "admission_year": 2025}]
    )
    courses = pd.DataFrame([{"id": "C1", "course_code": "CS101", "course_name": "Intro", "semester": 2}])
    assessments = pd.DataFrame(
        [
            {"student_id": "S1", "course_id": "C1", "assessment_type": "QUIZ", "score": 80, "maximum_score": 100, "assessment_date": "2026-01-10"},
            {"student_id": "S1", "course_id": "C1", "assessment_type": "QUIZ", "score": 60, "maximum_score": 100, "assessment_date": "2026-01-20"},
            {"student_id": "S1", "course_id": "C1", "assessment_type": "MIDTERM", "score": 70, "maximum_score": 100, "assessment_date": "2026-02-01"},
            {"student_id": "S1", "course_id": "C1", "assessment_type": "ENDTERM", "score": 65, "maximum_score": 100, "assessment_date": "2026-03-01"},
        ]
    )
    attendance = pd.DataFrame(
        [
            {"student_id": "S1", "course_id": "C1", "classes_conducted": 20, "classes_attended": 16, "date": "2026-01-31"},
            {"student_id": "S1", "course_id": "C1", "classes_conducted": 20, "classes_attended": 10, "date": "2026-02-28"},
        ]
    )
    activities = pd.DataFrame(
        [
            {"student_id": "S1", "course_id": "C1", "activity_date": "2026-01-15", "session_duration": 60, "videos_watched": 5, "videos_completed": 4, "documents_opened": 2, "quiz_attempts": 2, "assignments_submitted": 1, "late_submissions": 0, "practice_questions_attempted": 20, "login_count": 5},
            {"student_id": "S1", "course_id": "C1", "activity_date": "2026-01-22", "session_duration": 30, "videos_watched": 3, "videos_completed": 1, "documents_opened": 1, "quiz_attempts": 1, "assignments_submitted": 0, "late_submissions": 0, "practice_questions_attempted": 5, "login_count": 2},
        ]
    )
    return assessments, attendance, activities, students, courses


def test_feature_averages():
    assessments, attendance, activities, students, courses = _raw_frames()
    features = build_features(assessments, attendance, activities, students, courses)
    assert len(features) == 1
    row = features.iloc[0]
    assert row["quiz_average"] == pytest.approx(70.0)   # (80 + 60) / 2
    assert row["midterm_score"] == pytest.approx(70.0)
    assert row[TARGET_COLUMN] == pytest.approx(65.0)     # ENDTERM held out as target
    assert row["attendance_percentage"] == pytest.approx(65.0)  # 26 attended / 40 conducted


def test_endterm_not_counted_in_trend_features():
    assessments, attendance, activities, students, courses = _raw_frames()
    features = build_features(assessments, attendance, activities, students, courses)
    # assessment_count excludes ENDTERM (3 non-final records)
    assert features.iloc[0]["assessment_count"] == 3


def test_engagement_score_bounds_and_weights():
    total_weight = sum(ENGAGEMENT_WEIGHTS.values())
    assert abs(total_weight - 1.0) < 1e-9
    high = compute_engagement_score(1.0, 1.0, 7, 10, 4, 50, 0.0)
    low = compute_engagement_score(0.0, 0.0, 0, 0, 0, 0, 1.0)
    assert 0.0 <= low < 0.5 < high <= 1.0


def test_training_dataset_separates_target():
    assessments, attendance, activities, students, courses = _raw_frames()
    X, y = build_training_dataset(assessments, attendance, activities, students, courses)
    assert list(y) == [65.0]
    assert TARGET_COLUMN in X.columns
    assert set(FEATURE_COLUMNS).issubset(X.columns)


def test_risk_classification_thresholds():
    thresholds = get_risk_thresholds()
    assert thresholds.low < thresholds.medium < thresholds.high
    assert classify_risk(0.0) == "LOW"
    assert classify_risk(0.30) == "MEDIUM"
    assert classify_risk(0.60) == "HIGH"
    assert classify_risk(0.95) == "CRITICAL"


def test_risk_probability_fallback_mapping():
    assert _risk_probability_from_score(100) < 0.01
    assert abs(_risk_probability_from_score(50) - 0.5) < 1e-6
    assert _risk_probability_from_score(0) > 0.99


def test_predictor_loads_artifacts_and_predicts():
    """Full inference path with real trained artifacts (produced by the training run)."""
    from pathlib import Path

    import json

    from ml.config import METADATA_FILE, MODEL_CLASSIFICATION_FILE, MODEL_REGRESSION_FILE

    if not MODEL_REGRESSION_FILE.exists():
        import pytest

        pytest.skip("Trained artifacts not present — run `python -m ml.training.train` first")

    from ml.inference.predictor import PerformancePredictor

    predictor = PerformancePredictor()
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    assert metadata["models"]["regression"]["model_name"] == predictor.model_name

    assessments, attendance, activities, students, courses = _raw_frames()
    features = build_features(assessments, attendance, activities, students, courses)
    result = predictor.predict(features[FEATURE_COLUMNS])
    assert 0.0 <= result["predicted_score"] <= 100.0
    assert 0.0 <= result["risk_probability"] <= 1.0
