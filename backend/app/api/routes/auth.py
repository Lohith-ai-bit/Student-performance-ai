from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.core.errors import AuthError
from app.models import Student
from app.schemas.auth import (
    AuthMeResponse,
    LoginRequest,
    RefreshRequest,
    StudentRegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: StudentRegisterRequest, db: Session = Depends(get_db)):
    """Student self-registration (§8). All fields validated by Pydantic."""
    user = auth_service.register_student(db, payload)
    return auth_service.issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    return auth_service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(user=Depends(get_current_user)):
    # Stateless JWT: the client discards the token. Server-side revocation is a Phase 3 concern.
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=AuthMeResponse)
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    extra = {}
    if user.role.value == "STUDENT":
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            extra["student_id"] = str(student.id)
    payload = {"success": True, "user": user, **extra}
    return payload
