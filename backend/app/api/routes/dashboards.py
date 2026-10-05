"""Dashboard aggregate endpoints (§13/§16/§18)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_faculty, get_current_student, require_roles
from app.core.database import get_db
from app.models import User
from app.models.enums import Role
from app.services import dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/student")
def student_dashboard(
    student=Depends(get_current_student),
    db: Session = Depends(get_db),
):
    data = dashboard_service.student_dashboard(db, student)
    user = db.get(User, student.user_id)
    data["student"]["name"] = user.name
    return data


@router.get("/faculty")
def faculty_dashboard(
    faculty=Depends(get_current_faculty),
    db: Session = Depends(get_db),
):
    data = dashboard_service.faculty_dashboard(db, faculty)
    user = db.get(User, faculty.user_id)
    data["faculty_name"] = user.name
    return data


@router.get("/admin", dependencies=[Depends(require_roles(Role.ADMIN))])
def admin_dashboard(db: Session = Depends(get_db)):
    return dashboard_service.admin_dashboard(db)
