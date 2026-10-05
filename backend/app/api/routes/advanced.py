"""Phase 2/3 routes: unified ML prediction, explanations, recommendations,
registry/experiments, monitoring/drift, batch jobs, notifications, interventions."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_faculty, get_current_student, get_current_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models import (
    BatchPredictionJob, Course, Enrollment, ModelVersion, Prediction,
    Recommendation, RecommendationFeedback, Student, User,
)
from app.models.advanced_enums import ModelType, RecommendationStatus
from app.models.enums import Role
from app.schemas.advanced import (
    BatchJobOut, BatchPredictionRequest, DriftResponse, ExperimentOut,
    ExplanationResponse, InterventionCreate, ModelVersionOut,
    MonitoringResponse, NotificationOut, PredictAdvancedRequest,
    PredictionAdvancedResponse, RecommendationFeedbackRequest,
    RecommendationOut, RecommendationUpdate, ResourceOut,
)
from app.services import (
    explanation_service, monitoring_service, notification_service,
    ops_service, registry_service, recommendation_service,
)

router = APIRouter(tags=["advanced"])

AdminDeps = Depends(require_roles(Role.ADMIN))
StaffDeps = Depends(require_roles(Role.FACULTY, Role.ADMIN))


# ------------------------------------------------------------- unified ML predict
def _ensure_predict_access(db: Session, user, student_id, course_id):
    from app.api.routes.ml import _ensure_student_access

    return _ensure_student_access(db, user, student_id, course_id)


@router.post("/ml/predict/advanced", response_model=PredictionAdvancedResponse)
def predict_advanced(payload: PredictAdvancedRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Unified prediction (§18): model_type selectable; explanation + recommendations."""
    student = _ensure_predict_access(db, user, payload.student_id, payload.course_id)
    result = _run_engine(db, user, student, payload.course_id, "BASELINE", payload.explain, payload.recommend)
    return result


@router.post("/ml/transformer/predict", response_model=PredictionAdvancedResponse)
def predict_transformer(payload: PredictAdvancedRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    student = _ensure_predict_access(db, user, payload.student_id, payload.course_id)
    result = _run_engine(db, user, student, payload.course_id, "TRANSFORMER", payload.explain, payload.recommend)
    return result


@router.post("/ml/hybrid/predict", response_model=PredictionAdvancedResponse)
def predict_hybrid(payload: PredictAdvancedRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    student = _ensure_predict_access(db, user, payload.student_id, payload.course_id)
    result = _run_engine(db, user, student, payload.course_id, "HYBRID", payload.explain, payload.recommend)
    return result


def _run_engine(db: Session, user, student, course_id, model_type: str, explain: bool, recommend: bool) -> dict:
    from ml.inference.engine import predict as engine_predict

    previous = None
    if model_type != "BASELINE":
        pass
    result = engine_predict(
        db, student, course_id,
        model_type=model_type, persist=True, explain=explain, recommend=recommend,
    )
    monitoring_service.record_latency(result.get("latency_ms", 0))
    # notifications (§43): new prediction + risk change for the student
    if result.get("prediction_id"):
        notification_service.notify(
            db, student.user_id,
            title=f"New {model_type.lower()} prediction available",
            message=(
                f"Predicted score {result['predicted_score']}% with {result['risk_level']} risk. "
                "Open your dashboard for details and recommendations."
            ),
            notification_type="PREDICTION",
            link="/student/prediction",
        )
        ops_service.audit(db, user.id, "PREDICT", f"student:{student.id}", {"model_type": model_type})
    return result


# ------------------------------------------------------------------- explanations
@router.get("/predictions/{prediction_id}/explanation", response_model=ExplanationResponse)
def prediction_explanation(prediction_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    prediction = db.get(Prediction, prediction_id)
    if prediction is None:
        raise NotFoundError("Prediction could not be found.", code="PREDICTION_NOT_FOUND")
    # RBAC: students may only see their own; faculty see students in their courses; admin any
    if user.role == Role.STUDENT:
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student is None or prediction.student_id != student.id:
            raise ForbiddenError("You can only view explanations for your own predictions.", code="NOT_SELF")
    elif user.role == Role.FACULTY and user.faculty:
        course_ids = [c.id for c in user.faculty.courses]
        enrolled = (
            db.query(Enrollment.id)
            .filter(Enrollment.student_id == prediction.student_id, Enrollment.course_id.in_(course_ids))
            .first()
            if course_ids
            else None
        )
        if not enrolled:
            raise ForbiddenError("This student is not enrolled in your assigned courses.", code="STUDENT_NOT_IN_COURSE")

    data = explanation_service.get_explanation(db, prediction_id)
    if data is None:
        raise NotFoundError("Prediction could not be found.", code="PREDICTION_NOT_FOUND")
    prediction_payload = {
        "id": str(prediction.id),
        "predicted_score": prediction.predicted_score,
        "risk_probability": prediction.risk_probability,
        "risk_level": prediction.risk_level.value if hasattr(prediction.risk_level, "value") else str(prediction.risk_level),
        "model_name": prediction.model_name,
        "model_version": prediction.model_version,
        "model_type": prediction.model_type,
    }
    return {
        "success": True,
        "prediction": prediction_payload,
        "shap": data["shap"],
        "lime": data["lime"],
        "gradient": data["gradient"],
        "summary": data["summary"],
        "factors": data["factors"],
        "disclaimer": data["disclaimer"],
    }


# ----------------------------------------------------------------- recommendations
@router.get("/students/me/recommendations", response_model=list[RecommendationOut])
def my_recommendations(student=Depends(get_current_student), db: Session = Depends(get_db)):
    return (
        db.query(Recommendation)
        .filter(Recommendation.student_id == student.id)
        .order_by(Recommendation.score.desc())
        .limit(50)
        .all()
    )


@router.get("/students/{student_id}/recommendations", response_model=list[RecommendationOut], dependencies=[StaffDeps])
def student_recommendations_for_staff(student_id: uuid.UUID, db: Session = Depends(get_db)):
    """Faculty/admin view of a student's recommendations (§33)."""
    return (
        db.query(Recommendation)
        .filter(Recommendation.student_id == student_id)
        .order_by(Recommendation.score.desc())
        .limit(50)
        .all()
    )


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationOut)
def update_recommendation(
    recommendation_id: uuid.UUID, payload: RecommendationUpdate,
    student=Depends(get_current_student), db: Session = Depends(get_db),
):
    row = db.get(Recommendation, recommendation_id)
    if row is None or row.student_id != student.id:
        raise NotFoundError("Recommendation could not be found.", code="RECOMMENDATION_NOT_FOUND")
    from datetime import datetime, timezone

    row.status = payload.status
    if payload.status == RecommendationStatus.COMPLETED.value:
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.post("/recommendations/{recommendation_id}/feedback")
def recommend_feedback(
    recommendation_id: uuid.UUID, payload: RecommendationFeedbackRequest,
    student=Depends(get_current_student), db: Session = Depends(get_db),
):
    row = db.get(Recommendation, recommendation_id)
    if row is None or row.student_id != student.id:
        raise NotFoundError("Recommendation could not be found.", code="RECOMMENDATION_NOT_FOUND")
    feedback = RecommendationFeedback(
        recommendation_id=row.id, student_id=student.id,
        rating=payload.rating, helpful=payload.helpful, feedback_text=payload.feedback_text,
    )
    db.add(feedback)
    db.commit()
    ops_service.audit(db, None, "RECOMMENDATION_FEEDBACK", str(row.id), {"rating": payload.rating})
    return {"success": True, "message": "Feedback recorded. It will inform future ranking."}


@router.get("/students/me/learning-progress")
def learning_progress(student=Depends(get_current_student), db: Session = Depends(get_db)):
    from app.models import LearningActivity, Recommendation

    acts = db.query(LearningActivity).filter(LearningActivity.student_id == student.id).all()
    recs = db.query(Recommendation).filter(Recommendation.student_id == student.id).all()
    by_status = {}
    for r in recs:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "success": True,
        "learning_hours": round(sum(a.session_duration for a in acts) / 60.0, 1),
        "practice_questions": sum(a.practice_questions_attempted for a in acts),
        "recommendations_completed": by_status.get("COMPLETED", 0),
        "recommendations_in_progress": by_status.get("IN_PROGRESS", 0),
        "recommendations_total": len(recs),
        "by_status": by_status,
    }


# --------------------------------------------------------------------- resources
@router.get("/resources", response_model=list[ResourceOut])
def list_resources(
    user=Depends(get_current_user), db: Session = Depends(get_db),
    course_id: uuid.UUID | None = None, topic: str | None = None,
    difficulty: str | None = None, resource_type: str | None = None,
    search: str | None = None, limit: int = 60,
):
    from sqlalchemy import func

    from app.models import LearningResource

    query = db.query(LearningResource)
    if course_id:
        query = query.filter(LearningResource.course_id == course_id)
    if topic:
        query = query.filter(func.lower(LearningResource.topic).like(f"%{topic.lower()}%"))
    if difficulty:
        query = query.filter(LearningResource.difficulty == difficulty.upper())
    if resource_type:
        query = query.filter(LearningResource.resource_type == resource_type.upper())
    if search:
        query = query.filter(func.lower(LearningResource.title).like(f"%{search.lower()}%"))
    return query.limit(min(limit, 200)).all()


# ------------------------------------------------------------------ registry (§17)
@router.get("/ml/registry", response_model=list[ModelVersionOut], dependencies=[AdminDeps])
def registry(db: Session = Depends(get_db)):
    registry_service.sync_from_artifacts(db)
    return registry_service.list_models(db)


@router.post("/ml/registry/sync", response_model=list[ModelVersionOut], dependencies=[AdminDeps])
def registry_sync(db: Session = Depends(get_db)):
    registry_service.sync_from_artifacts(db)
    return registry_service.list_models(db)


@router.post("/ml/registry/{model_id}/promote", response_model=ModelVersionOut, dependencies=[AdminDeps])
def promote_model(model_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):
    row = registry_service.promote(db, model_id)
    ops_service.audit(db, user.id, "MODEL_PROMOTE", str(model_id), {"status": row.status})
    return row


@router.get("/ml/experiments", response_model=list[ExperimentOut])
def experiments(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not registry_service.list_experiments(db):
        registry_service.import_experiment_report(db)
    return registry_service.list_experiments(db)


# ---------------------------------------------------------------- batch (§41/§42)
@router.post("/ml/batch-predictions", response_model=BatchJobOut)
def create_batch_job(
    payload: BatchPredictionRequest, user=StaffDeps, db: Session = Depends(get_db),
):
    total = _count_scope(db, payload)
    job = ops_service.create_batch_job(
        db, user.id, payload.scope, payload.scope_id, payload.model_type, payload.model_version, total
    )
    if payload.run_inline or total <= 50:
        job = ops_service.process_batch_job(db, job.id)
    else:
        ops_service.enqueue_batch_job(job.id)
    ops_service.audit(db, user.id, "BATCH_PREDICT", payload.scope, {"job_id": str(job.id), "total": total})
    return job


def _count_scope(db: Session, payload: BatchPredictionRequest) -> int:
    from app.models import Department, Enrollment, Student

    scope = payload.scope.upper()
    if scope == "STUDENT":
        return 1
    if scope == "COURSE":
        course = db.get(Course, uuid.UUID(payload.scope_id)) if payload.scope_id else None
        return (
            db.query(Enrollment).filter(Enrollment.course_id == course.id).count() if course else 0
        )
    if scope == "DEPARTMENT":
        return db.query(Student).filter(Student.department == payload.scope_id).count()
    return 0


@router.get("/ml/batch-predictions/{job_id}", response_model=BatchJobOut)
def get_batch_job(job_id: uuid.UUID, user=StaffDeps, db: Session = Depends(get_db)):
    job = db.get(BatchPredictionJob, job_id)
    if job is None:
        raise NotFoundError("Batch job could not be found.", code="JOB_NOT_FOUND")
    return job


@router.post("/ml/batch-predictions/{job_id}/process", response_model=BatchJobOut, dependencies=[StaffDeps])
def process_batch_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return ops_service.process_batch_job(db, job_id)


# ---------------------------------------------------------------- interventions (§34)
@router.post("/interventions")
def create_intervention(
    payload: InterventionCreate, faculty=Depends(get_current_faculty), db: Session = Depends(get_db),
):
    from app.models import FacultyIntervention

    row = FacultyIntervention(
        faculty_id=faculty.id, student_id=payload.student_id, course_id=payload.course_id,
        prediction_id=payload.prediction_id, note=payload.note,
        intervention_type=payload.intervention_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # notify the student (supportive framing)
    student = db.get(Student, payload.student_id)
    if student:
        notification_service.notify(
            db, student.user_id,
            title="Your faculty added a supportive note",
            message=payload.note,
            notification_type="ALERT",
            link="/student/dashboard",
        )
    ops_service.audit(db, None, "INTERVENTION", str(row.id), {"type": payload.intervention_type})
    return {"success": True, "id": str(row.id), "message": "Intervention recorded."}


@router.get("/faculty/interventions")
def list_interventions(faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    from app.models import FacultyIntervention

    rows = (
        db.query(FacultyIntervention)
        .filter(FacultyIntervention.faculty_id == faculty.id)
        .order_by(FacultyIntervention.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "success": True,
        "items": [
            {
                "id": str(r.id), "student_id": str(r.student_id), "course_id": str(r.course_id) if r.course_id else None,
                "note": r.note, "intervention_type": r.intervention_type, "created_at": r.created_at,
            }
            for r in rows
        ],
    }


# ------------------------------------------------------------------- monitoring (§38/§39)
@router.get("/admin/monitoring", response_model=MonitoringResponse, dependencies=[AdminDeps])
def admin_monitoring(db: Session = Depends(get_db)):
    return {"success": True, "summary": monitoring_service.monitoring_summary(db), "drift": monitoring_service.drift_report(db)}


@router.get("/admin/drift", response_model=DriftResponse, dependencies=[AdminDeps])
def admin_drift(db: Session = Depends(get_db)):
    return monitoring_service.drift_report(db)


@router.get("/admin/model-performance")
def admin_model_performance(db: Session = Depends(get_db)):
    registry_service.sync_from_artifacts(db)
    models = registry_service.list_models(db)
    return {
        "success": True,
        "items": [
            {
                "id": str(m.id), "model_name": m.model_name, "model_type": m.model_type,
                "version": m.version, "status": m.status, "training_date": m.training_date,
                "metrics": m.metrics, "dataset_version": m.dataset_version,
                "feature_version": m.feature_version, "artifact_location": m.artifact_location,
            }
            for m in models
        ],
    }


@router.post("/admin/experiments/import")
def import_experiments(db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):
    count = registry_service.import_experiment_report(db)
    ops_service.audit(db, user.id, "EXPERIMENTS_IMPORT", None, {"imported": count})
    return {"success": True, "imported": count}


# ------------------------------------------------------------------ notifications
@router.get("/notifications", response_model=list[NotificationOut])
def my_notifications(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return notification_service.list_for_user(db, user.id)


@router.post("/notifications/read")
def read_notifications(user=Depends(get_current_user), db: Session = Depends(get_db), notification_id: uuid.UUID | None = None):
    count = notification_service.mark_read(db, user.id, notification_id)
    return {"success": True, "marked": count}
