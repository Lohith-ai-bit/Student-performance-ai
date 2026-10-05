"""API tests (§39): prediction endpoint, student endpoint, assessment endpoint."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from app.core.config import settings
from ml.preprocessing.pipeline import build_preprocessor
from ml.features.build_features import FEATURE_COLUMNS


@pytest.fixture
def trained_artifacts(tmp_path, monkeypatch):
    """Tiny real model trained on synthetic feature rows, pointed at via settings."""
    rng = np.random.default_rng(42)
    n = 80
    X = pd.DataFrame(
        {
            "quiz_average": rng.uniform(30, 100, n),
            "assignment_average": rng.uniform(30, 100, n),
            "midterm_score": rng.uniform(30, 100, n),
            "lab_average": [np.nan] * n,
            "project_average": [np.nan] * n,
            "assessment_count": rng.integers(3, 8, n).astype(float),
            "score_trend": rng.normal(0, 5, n),
            "attendance_percentage": rng.uniform(40, 100, n),
            "attendance_trend": rng.normal(0, 5, n),
            "logins_per_week": rng.uniform(0, 7, n),
            "session_hours_per_week": rng.uniform(0, 10, n),
            "documents_per_week": rng.uniform(0, 5, n),
            "quiz_attempts_per_week": rng.uniform(0, 4, n),
            "practice_questions_per_week": rng.uniform(0, 50, n),
            "videos_watched_per_week": rng.uniform(0, 10, n),
            "video_completion_rate": rng.uniform(0, 1, n),
            "assignments_submitted_per_week": rng.uniform(0, 2, n),
            "assignment_submission_rate": rng.uniform(0, 1, n),
            "late_submission_rate": rng.uniform(0, 1, n),
            "engagement_score": rng.uniform(0, 1, n),
            "previous_gpa": [np.nan] * n,
            "course_semester": rng.integers(1, 5, n).astype(float),
            "admission_year": [2025.0] * n,
            "department": rng.choice(["CSE", "ECE"], n),
            "branch": rng.choice(["CS", "EC"], n),
        }
    )
    y = (
        0.4 * X["quiz_average"]
        + 0.3 * X["midterm_score"]
        + 0.2 * X["attendance_percentage"]
        + 0.1 * X["engagement_score"] * 100
    )

    pipeline = Pipeline([("preprocessor", build_preprocessor()), ("model", LinearRegression())])
    pipeline.fit(X[FEATURE_COLUMNS], y)

    (tmp_path / "model_regression.joblib").write_bytes(b"")
    joblib.dump(pipeline, tmp_path / "model_regression.joblib")
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "trained_at": "2026-10-05T00:00:00+00:00",
                "dataset_version": "test",
                "feature_version": "v1",
                "models": {
                    "regression": {"model_name": "LinearRegression", "model_version": "test", "validation_metrics": {}, "test_metrics": {}, "all_validation_results": []},
                    "classification": {"model_name": "none", "model_version": "test", "validation_metrics": {}, "test_metrics": {}, "all_validation_results": []},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "ML_ARTIFACTS_DIR", str(tmp_path))
    return tmp_path


def test_student_profile_endpoint(client, auth_student, seed_users):
    response = client.get("/api/v1/students/me", headers=auth_student)
    assert response.status_code == 200
    body = response.json()
    assert body["roll_number"] == "S001"
    assert body["name"] == "Student"


def test_prediction_endpoint_with_trained_model(client, auth_student, auth_faculty, add_student_records, trained_artifacts):
    student = add_student_records["student"]
    response = client.post("/api/v1/ml/predict", json={"student_id": str(student.id), "course_id": None}, headers=auth_student)
    assert response.status_code == 200, response.text
    body = response.json()
    assert 0 <= body["predicted_score"] <= 100
    assert 0 <= body["risk_probability"] <= 1
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert body["model_name"] == "LinearRegression"

    # prediction persisted
    history = client.get("/api/v1/students/me/predictions/history", headers=auth_student)
    assert history.status_code == 200
    assert len(history.json()["history"]) >= 1


def test_prediction_without_data_returns_friendly_error(client, auth_student, seed_users):
    student = seed_users["student"]
    response = client.post("/api/v1/ml/predict", json={"student_id": str(student.id)}, headers=auth_student)
    assert response.status_code == 422
    assert "data" in response.json()["error"]["message"].lower()


def test_faculty_can_add_assessment(client, auth_faculty, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    response = client.post(
        "/api/v1/faculty/assessments",
        headers=auth_faculty,
        json={
            "student_id": str(student.id), "course_id": str(course.id),
            "assessment_type": "QUIZ", "score": 88, "maximum_score": 100,
            "assessment_date": "2026-09-15",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["assessment_type"] == "QUIZ"


def test_faculty_cannot_add_assessment_score_over_maximum(client, auth_faculty, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    response = client.post(
        "/api/v1/faculty/assessments",
        headers=auth_faculty,
        json={
            "student_id": str(student.id), "course_id": str(course.id),
            "assessment_type": "QUIZ", "score": 120, "maximum_score": 100,
            "assessment_date": "2026-09-15",
        },
    )
    assert response.status_code == 422


def test_faculty_attendance_percentage_computed_server_side(client, auth_faculty, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    response = client.post(
        "/api/v1/faculty/attendance",
        headers=auth_faculty,
        json={
            "student_id": str(student.id), "course_id": str(course.id),
            "classes_conducted": 20, "classes_attended": 15, "date": "2026-09-15",
        },
    )
    assert response.status_code == 201
    assert response.json()["attendance_percentage"] == 75.0


def test_csv_import_full_flow(client, auth_faculty, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    csv_content = (
        f"student_id,course,attendance,quiz_score,date\n"
        f"{student.roll_number},{course.course_code},80,75,2026-09-20\n"
        f"NOPE,{course.course_code},80,75,2026-09-20\n"
    ).encode()
    files = {"file": ("data.csv", csv_content, "text/csv")}

    preview = client.post("/api/v1/faculty/imports/csv/preview", headers=auth_faculty, files=files)
    assert preview.status_code == 200
    report = preview.json()["report"]
    assert report["valid_rows"] == 1 and report["invalid_rows"] == 1

    confirm = client.post("/api/v1/faculty/imports/csv/confirm", headers=auth_faculty, files=files)
    assert confirm.status_code == 200
    assert confirm.json()["report"]["inserted"] >= 1


def test_error_envelope_never_leaks_stack_traces(client, auth_admin):
    response = client.get("/api/v1/students/00000000-0000-0000-0000-000000000000", headers=auth_admin)
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "STUDENT_NOT_FOUND"
    assert "Traceback" not in json.dumps(body)
