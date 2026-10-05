"""Authentication business logic."""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import AuthError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Faculty, Student, User
from app.models.enums import Role
from app.schemas.auth import StudentRegisterRequest


def email_exists(db: Session, email: str) -> bool:
    return db.query(User.id).filter(User.email == email.lower()).first() is not None


def register_student(db: Session, payload: StudentRegisterRequest, admission_year: int | None = None) -> User:
    if email_exists(db, payload.email):
        raise ConflictError("An account with this email already exists.", code="EMAIL_ALREADY_EXISTS")
    if db.query(Student.id).filter(Student.roll_number == payload.roll_number).first():
        raise ConflictError("A student with this roll number already exists.", code="ROLL_NUMBER_EXISTS")

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=Role.STUDENT,
    )
    student = Student(
        user=user,
        roll_number=payload.roll_number.strip(),
        department=payload.department.strip(),
        branch=payload.branch.strip(),
        year=payload.year,
        semester=payload.semester,
        section=payload.section.strip(),
        admission_year=admission_year or date.today().year,
    )
    db.add(user)
    db.add(student)
    db.commit()
    db.refresh(user)
    return user


def create_faculty(
    db: Session, *, name: str, email: str, password: str,
    employee_id: str, department: str, designation: str, course_ids: list[str] | None = None,
) -> User:
    if email_exists(db, email):
        raise ConflictError("An account with this email already exists.", code="EMAIL_ALREADY_EXISTS")
    if db.query(Faculty.id).filter(Faculty.employee_id == employee_id).first():
        raise ConflictError("An employee with this ID already exists.", code="EMPLOYEE_ID_EXISTS")

    user = User(
        name=name.strip(),
        email=email.lower(),
        password_hash=hash_password(password),
        role=Role.FACULTY,
    )
    faculty = Faculty(
        user=user,
        employee_id=employee_id.strip(),
        department=department.strip(),
        designation=designation.strip(),
    )
    if course_ids:
        from app.models import Course

        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        faculty.courses = courses
    db.add(user)
    db.add(faculty)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    # constant-shape failure: same message whether email or password is wrong
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise AuthError("This account has been deactivated.", code="ACCOUNT_DISABLED")
    return user


def issue_tokens(user: User) -> dict:
    return {
        "access_token": create_access_token(str(user.id), user.role.value, user.email, user.name),
        "refresh_token": create_refresh_token(str(user.id), user.role.value, user.email, user.name),
        "user": user,
    }


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise AuthError("Invalid refresh token.", code="INVALID_REFRESH_TOKEN")
    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type.", code="INVALID_REFRESH_TOKEN")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("User account is not available.", code="ACCOUNT_DISABLED")
    return issue_tokens(user)


def get_student_by_user(db: Session, user_id: uuid.UUID) -> Student:
    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student is None:
        raise NotFoundError("Student profile not found.", code="STUDENT_NOT_FOUND")
    return student
