"""FastAPI dependencies: JWT extraction and role-based access control."""
import uuid

import jwt as pyjwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_token
from app.models import Faculty, Student, User
from app.models.enums import Role


def _extract_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    # fallback: cookie (set by frontend for middleware-based redirects)
    token = request.cookies.get("spa_token")
    if token:
        return token
    raise AuthError("Missing authentication token.")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise AuthError("Token has expired. Please log in again.")
    except pyjwt.InvalidTokenError:
        raise AuthError("Invalid authentication token.")
    if payload.get("type") != "access":
        raise AuthError("Invalid token type.")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token payload.")
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise AuthError("Invalid token subject.")
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise AuthError("User account is not available.")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("Your role does not have access to this resource.")
        return user

    return checker


def get_current_student(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Student:
    if user.role != Role.STUDENT:
        raise ForbiddenError("This endpoint is restricted to students.")
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if student is None:
        raise ForbiddenError("No student profile is linked to this account.")
    return student


def get_current_faculty(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Faculty:
    if user.role != Role.FACULTY:
        raise ForbiddenError("This endpoint is restricted to faculty.")
    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    if faculty is None:
        raise ForbiddenError("No faculty profile is linked to this account.")
    return faculty
