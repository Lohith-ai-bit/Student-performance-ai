"""Student self-service endpoints (§10): a student sees ONLY their own data."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_student
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import Assessment, Attendance, Course, Enrollment, LearningActivity, Student, User
from app.schemas.records import AssessmentOut, AttendanceOut, LearningActivityOut
from app.schemas.users import StudentOut
from app.services import dashboard_service, prediction_service

router = APIRouter(prefix="/students", tags=["students"])


def _student_user(db: Session, student: Student) -> User:
    return db.get(User, student.user_id)


@router.get("/me", response_model=StudentOut)
def my_profile(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    user = _student_user(db, student)
    return StudentOut(
        id=str(student.id), name=user.name, email=user.email, roll_number=student.roll_number,
        department=student.department, branch=student.branch, year=student.year,
        semester=student.semester, section=student.section, admission_year=student.admission_year,
    )


@router.get("/me/courses")
def my_courses(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    items = []
    for e in enrollments:
        course = db.get(Course, e.course_id)
        items.append(
            {
                "enrollment_id": str(e.id), "course_id": str(course.id),
                "course_code": course.course_code, "course_name": course.course_name,
                "credits": course.credits, "academic_year": e.academic_year, "semester": e.semester,
            }
        )
    return {"success": True, "items": items}


@router.get("/me/assessments", response_model=list[AssessmentOut])
def my_assessments(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = (
        db.query(Assessment)
        .filter(Assessment.student_id == student.id)
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    return rows


@router.get("/me/attendance", response_model=list[AttendanceOut])
def my_attendance(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = (
        db.query(Attendance)
        .filter(Attendance.student_id == student.id)
        .order_by(Attendance.date.desc())
        .all()
    )
    return rows


@router.get("/me/activities", response_model=list[LearningActivityOut])
def my_activities(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = (
        db.query(LearningActivity)
        .filter(LearningActivity.student_id == student.id)
        .order_by(LearningActivity.activity_date.desc())
        .limit(500)
        .all()
    )
    return rows


@router.get("/me/predictions")
def my_predictions(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    latest = prediction_service.get_latest(db, student)
    history = prediction_service.get_history(db, student)
    return {
        "success": True,
        "latest": latest,
        "history": history,
        "disclaimer": (
            "This prediction is an AI-generated estimate intended to support learning and "
            "academic intervention. It should not be treated as a definitive judgment of student ability."
        ),
    }


@router.get("/me/predictions/history")
def my_prediction_history(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    history = prediction_service.get_history(db, student)
    return {"success": True, "history": history}


@router.get("/me/dashboard")
def my_dashboard(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    data = dashboard_service.student_dashboard(db, student)
    user = _student_user(db, student)
    data["student"]["name"] = user.name
    return data
