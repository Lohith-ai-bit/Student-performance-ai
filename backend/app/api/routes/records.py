"""Shared record endpoints: /assessments, /attendance, /learning-activities.

- Faculty/Admin: POST create (faculty must own the course), GET by student/course.
- Students: GET only their own records.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_faculty, get_current_student, require_roles
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models import Assessment, Attendance, Enrollment, LearningActivity, Student
from app.models.enums import Role
from app.schemas.records import (
    AssessmentCreate, AssessmentOut, AttendanceCreate, AttendanceOut,
    LearningActivityCreate, LearningActivityOut,
)
from app.models.attendance import compute_attendance_percentage

router = APIRouter(tags=["records"])

StaffDeps = Depends(require_roles(Role.FACULTY, Role.ADMIN))


def _ensure_student_enrolled(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> None:
    exists = (
        db.query(Enrollment.id)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
        .first()
    )
    if not exists:
        raise ForbiddenError("The student is not enrolled in this course.", code="STUDENT_NOT_ENROLLED")


def _ensure_course_access(faculty, course_id: uuid.UUID) -> None:
    if course_id not in {c.id for c in faculty.courses}:
        raise ForbiddenError("You are not assigned to this course.", code="COURSE_NOT_ASSIGNED")


# ------------------------------------------------------------------ assessments
@router.post("/assessments", response_model=AssessmentOut, status_code=201, dependencies=[StaffDeps])
def create_assessment(payload: AssessmentCreate, faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    _ensure_course_access(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    row = Assessment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/assessments", response_model=list[AssessmentOut], dependencies=[StaffDeps])
def list_assessments(
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    query = db.query(Assessment)
    if student_id:
        query = query.filter(Assessment.student_id == student_id)
    if course_id:
        query = query.filter(Assessment.course_id == course_id)
    return query.order_by(Assessment.assessment_date.desc()).limit(1000).all()


# ------------------------------------------------------------------- attendance
@router.post("/attendance", response_model=AttendanceOut, status_code=201, dependencies=[StaffDeps])
def create_attendance(payload: AttendanceCreate, faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    _ensure_course_access(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    data = payload.model_dump()
    data["attendance_percentage"] = compute_attendance_percentage(
        data["classes_conducted"], data["classes_attended"]
    )
    row = Attendance(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/attendance", response_model=list[AttendanceOut], dependencies=[StaffDeps])
def list_attendance(
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    query = db.query(Attendance)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if course_id:
        query = query.filter(Attendance.course_id == course_id)
    return query.order_by(Attendance.date.desc()).limit(1000).all()


# ----------------------------------------------------------- learning activities
@router.post("/learning-activities", response_model=LearningActivityOut, status_code=201, dependencies=[StaffDeps])
def create_activity(payload: LearningActivityCreate, faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    _ensure_course_access(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    row = LearningActivity(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/learning-activities", response_model=list[LearningActivityOut], dependencies=[StaffDeps])
def list_activities(
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    query = db.query(LearningActivity)
    if student_id:
        query = query.filter(LearningActivity.student_id == student_id)
    if course_id:
        query = query.filter(LearningActivity.course_id == course_id)
    return query.order_by(LearningActivity.activity_date.desc()).limit(1000).all()
