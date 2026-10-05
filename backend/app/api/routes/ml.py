"""ML endpoints (§30): prediction API, model registry, evaluations.

RBAC (§10):
- STUDENT may predict for themselves only.
- FACULTY may predict for students enrolled in their assigned courses.
- ADMIN may predict for anyone.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_faculty, get_current_student, get_current_user
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models import Enrollment, Student
from app.models.enums import Role
from app.schemas.predictions import (
    EvaluationResponse, ModelInfo, ModelsResponse, PredictRequest, PredictionResponse,
)
from app.services import model_service, prediction_service

router = APIRouter(prefix="/ml", tags=["ml"])


def _ensure_student_access(db: Session, user, student_id: uuid.UUID, course_id: uuid.UUID | None) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student could not be found.", code="STUDENT_NOT_FOUND")

    if user.role == Role.ADMIN:
        return student

    if user.role == Role.STUDENT:
        if student.user_id != user.id:
            raise ForbiddenError("Students can only request their own predictions.", code="NOT_SELF")
        return student

    # FACULTY: student must be enrolled in one of the faculty's courses
    course_ids = [c.id for c in user.faculty.courses] if user.faculty else []
    if not course_ids:
        raise ForbiddenError("You have no assigned courses.", code="NO_ASSIGNED_COURSES")
    scope = [course_id] if course_id else course_ids
    enrolled = (
        db.query(Enrollment.id)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id.in_(scope))
        .first()
    )
    if not enrolled:
        raise ForbiddenError("This student is not enrolled in your assigned courses.", code="STUDENT_NOT_IN_COURSE")
    return student


@router.post("/predict", response_model=PredictionResponse)
def predict(
    payload: PredictRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = _ensure_student_access(db, user, payload.student_id, payload.course_id)
    result = prediction_service.generate_prediction(db, student, payload.course_id)
    return result


@router.get("/models", response_model=ModelsResponse)
def list_models(user=Depends(get_current_user)):
    return {"success": True, "models": model_service.list_models()}


@router.get("/evaluate", response_model=EvaluationResponse)
def list_evaluations(user=Depends(get_current_user)):
    return {"success": True, "evaluations": model_service.list_evaluations()}
