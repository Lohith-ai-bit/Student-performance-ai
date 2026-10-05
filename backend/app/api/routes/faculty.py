"""Faculty endpoints (§10/§17/§19/§33): scoped to the courses assigned to the logged-in faculty."""
import math
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies.auth import get_current_faculty
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models import (
    Assessment, Attendance, Course, Enrollment, LearningActivity, Prediction,
    Student, User,
)
from app.schemas.records import (
    AssessmentCreate, AssessmentOut, AttendanceCreate, AttendanceOut,
    LearningActivityCreate, LearningActivityOut,
)
from app.services import import_service, prediction_service

router = APIRouter(prefix="/faculty", tags=["faculty"])


def _assigned_course_ids(db: Session, faculty) -> list[uuid.UUID]:
    faculty = (
        db.query(type(faculty)).options(joinedload(type(faculty).courses)).filter_by(id=faculty.id).first()
        or faculty
    )
    return [c.id for c in faculty.courses]


def _ensure_course_assigned(faculty, course_id: uuid.UUID) -> None:
    if course_id not in {c.id for c in faculty.courses}:
        raise ForbiddenError("You are not assigned to this course.", code="COURSE_NOT_ASSIGNED")


@router.get("/me/courses")
def my_courses(faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    courses = (
        db.query(Course)
        .filter(Course.id.in_(_assigned_course_ids(db, faculty)))
        .all()
        if faculty.courses
        else []
    )
    items = [
        {"id": str(c.id), "course_code": c.course_code, "course_name": c.course_name, "credits": c.credits, "semester": c.semester}
        for c in courses
    ]
    return {"success": True, "items": items}


@router.get("/students")
def student_table(
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
    year: int | None = None,
    semester: int | None = None,
    risk_level: str | None = None,
    course_id: uuid.UUID | None = None,
):
    """Student table with search, pagination, sorting, filtering (§17)."""
    course_ids = _assigned_course_ids(db, faculty)
    if course_id:
        _ensure_course_assigned(faculty, course_id)
        course_ids = [course_id]
    if not course_ids:
        return {"success": True, "items": [], "meta": {"page": page, "page_size": page_size, "total": 0, "total_pages": 0}}

    query = (
        db.query(Student, User)
        .join(User, Student.user_id == User.id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id.in_(course_ids))
        .distinct()
    )
    count_query = query
    if search:
        like = f"%{search.lower()}%"
        count_query = count_query.filter(or_(func.lower(User.name).like(like), func.lower(Student.roll_number).like(like)))
    if department:
        count_query = count_query.filter(func.lower(Student.department) == department.lower())
    if year is not None:
        count_query = count_query.filter(Student.year == year)
    if semester is not None:
        count_query = count_query.filter(Student.semester == semester)

    total = count_query.count()
    rows = (
        count_query.order_by(Student.roll_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # latest prediction per student in these courses
    latest_pred = {}
    if rows:
        student_ids = [s.id for s, _ in rows]
        preds = (
            db.query(Prediction)
            .filter(Prediction.student_id.in_(student_ids))
            .filter(Prediction.course_id.in_(course_ids))
            .order_by(Prediction.prediction_date.desc())
            .all()
        )
        for p in preds:
            latest_pred.setdefault(p.student_id, p)

    items = []
    for s, u in rows:
        p = latest_pred.get(s.id)
        items.append(
            {
                "student_id": str(s.id), "name": u.name, "email": u.email,
                "roll_number": s.roll_number, "department": s.department, "branch": s.branch,
                "year": s.year, "semester": s.semester, "section": s.section,
                "risk_level": p.risk_level.value if p else None,
                "predicted_score": p.predicted_score if p else None,
                "prediction_date": p.prediction_date if p else None,
            }
        )

    if risk_level:
        items = [i for i in items if i["risk_level"] == risk_level.upper()]

    return {
        "success": True,
        "items": items,
        "meta": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": math.ceil(total / page_size) if page_size else 0,
        },
    }


@router.get("/students/{student_id}")
def student_detail(
    student_id: uuid.UUID,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    """Full detail view for one student — §33 shows performance/attendance/activity + prediction."""
    course_ids = _assigned_course_ids(db, faculty)
    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id.in_(course_ids))
        .first()
        if course_ids
        else None
    )
    if not enrolled:
        raise ForbiddenError("This student is not enrolled in your assigned courses.", code="STUDENT_NOT_IN_COURSE")

    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student could not be found.", code="STUDENT_NOT_FOUND")
    user = db.get(User, student.user_id)

    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id, Assessment.course_id.in_(course_ids))
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    attendance = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id, Attendance.course_id.in_(course_ids))
        .order_by(Attendance.date.desc())
        .all()
    )
    activities = (
        db.query(LearningActivity)
        .filter(LearningActivity.student_id == student_id, LearningActivity.course_id.in_(course_ids))
        .order_by(LearningActivity.activity_date.desc())
        .limit(200)
        .all()
    )
    predictions = (
        db.query(Prediction)
        .filter(Prediction.student_id == student_id, Prediction.course_id.in_(course_ids))
        .order_by(Prediction.prediction_date.desc())
        .limit(50)
        .all()
    )

    def _orm_list(rows):
        return [
            {
                **{c.name: getattr(r, c.name) for c in r.__table__.columns},
            }
            for r in rows
        ]

    return {
        "success": True,
        "student": {
            "student_id": str(student.id), "name": user.name, "email": user.email,
            "roll_number": student.roll_number, "department": student.department,
            "branch": student.branch, "year": student.year, "semester": student.semester,
            "section": student.section,
        },
        "assessments": _orm_list(assessments),
        "attendance": _orm_list(attendance),
        "activities": _orm_list(activities),
        "predictions": _orm_list(predictions),
    }


# --------------------------------------------------------------- data entry (§19)
@router.post("/assessments", response_model=AssessmentOut, status_code=201)
def add_assessment(
    payload: AssessmentCreate,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    _ensure_course_assigned(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    row = Assessment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/attendance", response_model=AttendanceOut, status_code=201)
def add_attendance(
    payload: AttendanceCreate,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    _ensure_course_assigned(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    from app.models.attendance import compute_attendance_percentage

    data = payload.model_dump()
    data["attendance_percentage"] = compute_attendance_percentage(
        data["classes_conducted"], data["classes_attended"]
    )
    row = Attendance(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/activities", response_model=LearningActivityOut, status_code=201)
def add_activity(
    payload: LearningActivityCreate,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    _ensure_course_assigned(faculty, payload.course_id)
    _ensure_student_enrolled(db, payload.student_id, payload.course_id)
    row = LearningActivity(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _ensure_student_enrolled(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> None:
    exists = (
        db.query(Enrollment.id)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
        .first()
    )
    if not exists:
        raise ForbiddenError("The student is not enrolled in this course.", code="STUDENT_NOT_ENROLLED")


@router.get("/students/{student_id}/predict")
def predict_for_student(
    student_id: uuid.UUID,
    course_id: uuid.UUID | None = None,
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    """§33: faculty selects a student and generates a prediction."""
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student could not be found.", code="STUDENT_NOT_FOUND")
    if course_id:
        _ensure_course_assigned(faculty, course_id)
    else:
        course_ids = _assigned_course_ids(db, faculty)
        enrolled = (
            db.query(Enrollment.course_id)
            .filter(Enrollment.student_id == student_id, Enrollment.course_id.in_(course_ids))
            .first()
            if course_ids
            else None
        )
        if not enrolled:
            raise ForbiddenError("This student is not enrolled in your assigned courses.", code="STUDENT_NOT_IN_COURSE")
    return prediction_service.generate_prediction(db, student, course_id)


# ------------------------------------------------------------------ CSV import (§20)
@router.post("/imports/csv/preview")
def csv_preview(file: UploadFile = File(...), faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    content = file.file.read()
    rows, report = import_service.parse_and_validate(content, file.filename or "upload.csv", db)
    return {"success": True, "report": report.model_dump(), "preview_rows": rows[:50]}


@router.post("/imports/csv/confirm")
def csv_confirm(file: UploadFile = File(...), faculty=Depends(get_current_faculty), db: Session = Depends(get_db)):
    content = file.file.read()
    rows, report = import_service.parse_and_validate(content, file.filename or "upload.csv", db)
    result = import_service.import_rows(db, rows, file.filename or "upload.csv", report.invalid_rows)
    return {"success": True, "report": result.model_dump()}
