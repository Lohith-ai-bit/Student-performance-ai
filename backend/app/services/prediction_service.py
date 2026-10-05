"""Prediction orchestration (§30):

    Student ID -> retrieve data -> feature engineering -> load trained model
    -> prediction -> risk calculation -> store prediction -> return result
"""
import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.risk_config import classify_risk
from app.models import Course, Prediction, Student
from app.models.enums import RiskLevel
from app.services import feature_service


def _predictor():
    from ml.inference.predictor import PerformancePredictor

    return PerformancePredictor()  # loads artifacts lazily, cached per instance


def generate_prediction(
    db: Session,
    student: Student,
    course_id: uuid.UUID | None = None,
    predictor=None,
) -> dict:
    if course_id is not None:
        course = db.get(Course, course_id)
        if course is None:
            raise NotFoundError("Course could not be found.", code="COURSE_NOT_FOUND")

    predictor = predictor or _predictor()
    features = feature_service.build_student_feature_frame(db, student, course_id)
    if features.empty:
        raise ValidationError(
            "No assessment, attendance, or learning-activity data is available for this "
            "student yet. Add data and try again.",
            code="INSUFFICIENT_DATA",
        )

    predictions: list[dict] = []
    per_course_rows: list[dict] = []
    for (sid, cid), row in features.iterrows():
        result = predictor.predict(row.to_frame().T)
        predictions.append(result)
        per_course_rows.append({"course_id": cid, **result})

    # course-scoped call: single row; aggregate call: average across the student's courses
    predicted_score = round(
        sum(p["predicted_score"] for p in predictions if p["predicted_score"] is not None)
        / max(1, len([p for p in predictions if p["predicted_score"] is not None])),
        2,
    )
    risk_probability = round(sum(p["risk_probability"] for p in predictions) / len(predictions), 4)
    risk_level = classify_risk(risk_probability)

    meta = predictor.info()
    stored: list[Prediction] = []
    for row in per_course_rows:
        prediction = Prediction(
            student_id=student.id,
            course_id=uuid.UUID(row["course_id"]),
            model_name=meta.get("model_name", "unknown"),
            model_version=str(meta.get("model_version", "unknown")),
            predicted_score=row["predicted_score"] or 0.0,
            risk_probability=row["risk_probability"],
            risk_level=RiskLevel(risk_level),
        )
        db.add(prediction)
        stored.append(prediction)
    db.commit()

    return {
        "student_id": str(student.id),
        "course_id": str(course_id) if course_id else None,
        "predicted_score": predicted_score,
        "risk_probability": risk_probability,
        "risk_level": risk_level,
        "model_name": meta.get("model_name", "unknown"),
        "model_version": str(meta.get("model_version", "unknown")),
        "prediction_id": str(stored[0].id) if stored else "",
        "per_course": per_course_rows,
    }


def get_history(db: Session, student: Student, limit: int = 100) -> list[Prediction]:
    return (
        db.query(Prediction)
        .filter(Prediction.student_id == student.id)
        .order_by(Prediction.prediction_date.desc())
        .limit(limit)
        .all()
    )


def get_latest(db: Session, student: Student, course_id: uuid.UUID | None = None) -> Prediction | None:
    query = db.query(Prediction).filter(Prediction.student_id == student.id)
    if course_id is not None:
        query = query.filter(Prediction.course_id == course_id)
    return query.order_by(Prediction.prediction_date.desc()).first()
