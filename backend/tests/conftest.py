"""Shared test fixtures: SQLite-backed app + client + authenticated headers."""
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for path in (str(PROJECT_ROOT / "backend"), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Assessment, Attendance, Course, Department, Enrollment, Faculty,
    LearningActivity, Student, User,
)
from app.core.security import hash_password  # noqa: E402
from app.models.enums import Role  # noqa: E402

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_users(db_session):
    """One admin, one faculty (teaching one course), one student (enrolled in that course)."""
    admin = User(name="Admin", email="admin@test.edu", password_hash=hash_password("Admin@1234"), role=Role.ADMIN)
    faculty_user = User(name="Faculty", email="faculty@test.edu", password_hash=hash_password("Faculty@123"), role=Role.FACULTY)
    student_user = User(name="Student", email="student@test.edu", password_hash=hash_password("Student@123"), role=Role.STUDENT)
    db_session.add_all([admin, faculty_user, student_user])
    db_session.flush()

    department = Department(name="Computer Science", code="CSE")
    db_session.add(department)
    db_session.flush()

    faculty = Faculty(user_id=faculty_user.id, employee_id="F001", department="Computer Science", designation="Professor")
    db_session.add(faculty)
    db_session.flush()

    course = Course(course_code="CS101", course_name="Intro to CS", credits=3, department_id=department.id, semester=3)
    db_session.add(course)
    db_session.flush()
    faculty.courses = [course]

    student = Student(
        user_id=student_user.id, roll_number="S001", department="CSE", branch="CS",
        year=2, semester=3, section="A", admission_year=2025,
    )
    db_session.add(student)
    db_session.flush()
    db_session.add(Enrollment(student_id=student.id, course_id=course.id, academic_year=2026, semester=3))

    db_session.commit()
    return {
        "admin": admin,
        "faculty_user": faculty_user,
        "student_user": student_user,
        "faculty": faculty,
        "student": student,
        "course": course,
        "department": department,
    }


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_admin(client, seed_users):
    return login(client, "admin@test.edu", "Admin@1234")


@pytest.fixture
def auth_faculty(client, seed_users):
    return login(client, "faculty@test.edu", "Faculty@123")


@pytest.fixture
def auth_student(client, seed_users):
    return login(client, "student@test.edu", "Student@123")


@pytest.fixture
def add_student_records(db_session, seed_users):
    """Assessments + attendance + activity for the seeded student (feature-ready)."""
    from datetime import date

    student = seed_users["student"]
    course = seed_users["course"]

    for day, a_type, score in [
        (date(2026, 8, 20), "QUIZ", 70),
        (date(2026, 8, 27), "QUIZ", 80),
        (date(2026, 9, 5), "ASSIGNMENT", 85),
        (date(2026, 9, 15), "MIDTERM", 75),
    ]:
        db_session.add(Assessment(student_id=student.id, course_id=course.id, assessment_type=a_type, score=score, maximum_score=100.0, assessment_date=day))
    db_session.add(Attendance(student_id=student.id, course_id=course.id, classes_conducted=20, classes_attended=17, attendance_percentage=85.0, date=date(2026, 9, 1)))
    db_session.add(LearningActivity(student_id=student.id, course_id=course.id, activity_date=date(2026, 9, 10), session_duration=60, videos_watched=5, videos_completed=4, quiz_attempts=2, assignments_submitted=1, late_submissions=0, practice_questions_attempted=20, login_count=4))
    db_session.commit()
    return seed_users
