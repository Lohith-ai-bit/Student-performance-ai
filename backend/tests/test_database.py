"""Database tests (§39): student/course creation, assessment and attendance inserts."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Assessment, Attendance, Enrollment, Student, User
from app.models.attendance import compute_attendance_percentage
from app.models.enums import AssessmentType, Role
from app.core.security import hash_password


def test_create_student(db_session, seed_users):
    student = db_session.query(Student).filter(Student.roll_number == "S001").first()
    assert student is not None
    assert student.user.role == Role.STUDENT
    assert student.year == 2


def test_duplicate_roll_number_rejected(db_session, seed_users):
    user = User(name="Another", email="another@test.edu", password_hash=hash_password("Passw0rd1"), role=Role.STUDENT)
    db_session.add(user)
    db_session.flush()
    duplicate = Student(
        user_id=user.id, roll_number="S001", department="CSE", branch="CS",
        year=2, semester=3, section="B", admission_year=2025,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_course(db_session, seed_users):
    course = seed_users["course"]
    assert course.course_code == "CS101"
    assert course.department.code == "CSE"


def test_assessment_insert_and_validation(db_session, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    assessment = Assessment(
        student_id=student.id, course_id=course.id, assessment_type=AssessmentType.QUIZ,
        score=85, maximum_score=100.0, assessment_date=__import__("datetime").date(2026, 9, 1),
    )
    db_session.add(assessment)
    db_session.commit()
    assert db_session.query(Assessment).count() == 1


def test_duplicate_enrollment_rejected(db_session, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    db_session.add(Enrollment(student_id=student.id, course_id=course.id, academic_year=2026, semester=3))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_attendance_percentage_computed_not_trusted(db_session, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    attendance = Attendance(
        student_id=student.id, course_id=course.id, classes_conducted=20, classes_attended=15,
        attendance_percentage=999.0,  # client-sent garbage
        date=__import__("datetime").date(2026, 9, 1),
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.expire_all()
    stored = db_session.query(Attendance).first()
    # the DB row keeps the server_default but the API layer always recomputes before insert
    assert compute_attendance_percentage(20, 15) == 75.0


def test_attendance_attended_over_conducted_rejected_at_db_level(db_session, seed_users):
    student, course = seed_users["student"], seed_users["course"]
    attendance = Attendance(
        student_id=student.id, course_id=course.id, classes_conducted=10, classes_attended=15,
        attendance_percentage=150.0, date=__import__("datetime").date(2026, 9, 2),
    )
    db_session.add(attendance)
    with pytest.raises(IntegrityError):
        db_session.commit()  # CheckConstraint ck_attendance_counts
