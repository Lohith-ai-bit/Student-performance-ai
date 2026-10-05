"""Admin management endpoints (§10): students, faculty, departments, courses, enrollments."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models import Course, Department, Enrollment, Student, User
from app.models.enums import Role
from app.schemas.courses import CourseCreate, CourseOut, CourseUpdate, DepartmentCreate, DepartmentOut, EnrollmentCreate, EnrollmentOut
from app.schemas.users import FacultyCreate, FacultyOut, FacultyUpdate, StudentCreate, StudentOut, StudentUpdate
from app.services import auth_service

router = APIRouter(tags=["admin"])

AdminDeps = Depends(require_roles(Role.ADMIN))


# ----------------------------------------------------------------- departments
@router.get("/departments", response_model=list[DepartmentOut], dependencies=[AdminDeps])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut, status_code=201, dependencies=[AdminDeps])
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    exists = db.query(Department.id).filter(Department.code == payload.code.upper()).first()
    if exists:
        raise ConflictError("A department with this code already exists.", code="DEPARTMENT_EXISTS")
    row = Department(name=payload.name.strip(), code=payload.code.upper().strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/departments/{department_id}", dependencies=[AdminDeps])
def delete_department(department_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Department, department_id)
    if row is None:
        raise NotFoundError("Department could not be found.", code="DEPARTMENT_NOT_FOUND")
    db.delete(row)
    db.commit()
    return {"success": True, "message": "Department deleted."}


# ---------------------------------------------------------------------- courses
@router.get("/courses", response_model=list[CourseOut], dependencies=[AdminDeps])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.course_code).all()


@router.post("/courses", response_model=CourseOut, status_code=201, dependencies=[AdminDeps])
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    row = Course(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/courses/{course_id}", response_model=CourseOut, dependencies=[AdminDeps])
def update_course(course_id: uuid.UUID, payload: CourseUpdate, db: Session = Depends(get_db)):
    row = db.get(Course, course_id)
    if row is None:
        raise NotFoundError("Course could not be found.", code="COURSE_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/courses/{course_id}", dependencies=[AdminDeps])
def delete_course(course_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Course, course_id)
    if row is None:
        raise NotFoundError("Course could not be found.", code="COURSE_NOT_FOUND")
    db.delete(row)
    db.commit()
    return {"success": True, "message": "Course deleted."}


# ------------------------------------------------------------------ enrollments
@router.post("/enrollments", response_model=EnrollmentOut, status_code=201, dependencies=[AdminDeps])
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)):
    dup = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.student_id == payload.student_id,
            Enrollment.course_id == payload.course_id,
            Enrollment.academic_year == payload.academic_year,
            Enrollment.semester == payload.semester,
        )
        .first()
    )
    if dup:
        raise ConflictError("This enrollment already exists.", code="ENROLLMENT_EXISTS")
    row = Enrollment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/enrollments", response_model=list[EnrollmentOut], dependencies=[AdminDeps])
def list_enrollments(student_id: uuid.UUID | None = None, course_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(Enrollment)
    if student_id:
        query = query.filter(Enrollment.student_id == student_id)
    if course_id:
        query = query.filter(Enrollment.course_id == course_id)
    return query.limit(1000).all()


# --------------------------------------------------------------------- students
@router.get("/students", response_model=list[StudentOut], dependencies=[AdminDeps])
def list_students(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = None,
    department: str | None = None,
    year: int | None = None,
    semester: int | None = None,
):
    query = db.query(Student, User).join(User, Student.user_id == User.id)
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import func, or_

        query = query.filter(or_(func.lower(User.name).like(like), func.lower(Student.roll_number).like(like)))
    if department:
        from sqlalchemy import func

        query = query.filter(func.lower(Student.department) == department.lower())
    if year is not None:
        query = query.filter(Student.year == year)
    if semester is not None:
        query = query.filter(Student.semester == semester)

    rows = (
        query.order_by(Student.roll_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [
        StudentOut(
            id=str(s.id), name=u.name, email=u.email, roll_number=s.roll_number,
            department=s.department, branch=s.branch, year=s.year, semester=s.semester,
            section=s.section, admission_year=s.admission_year,
        )
        for s, u in rows
    ]


@router.post("/students", response_model=StudentOut, status_code=201, dependencies=[AdminDeps])
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    user = auth_service.register_student(db, payload, payload.admission_year)
    student = db.query(Student).filter(Student.user_id == user.id).first()
    return StudentOut(
        id=str(student.id), name=user.name, email=user.email, roll_number=student.roll_number,
        department=student.department, branch=student.branch, year=student.year,
        semester=student.semester, section=student.section, admission_year=student.admission_year,
    )


@router.patch("/students/{student_id}", response_model=StudentOut, dependencies=[AdminDeps])
def update_student(student_id: uuid.UUID, payload: StudentUpdate, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student could not be found.", code="STUDENT_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    user = db.get(User, student.user_id)
    return StudentOut(
        id=str(student.id), name=user.name, email=user.email, roll_number=student.roll_number,
        department=student.department, branch=student.branch, year=student.year,
        semester=student.semester, section=student.section, admission_year=student.admission_year,
    )


@router.get("/students/{student_id}", response_model=StudentOut, dependencies=[AdminDeps])
def get_student(student_id: uuid.UUID, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student could not be found.", code="STUDENT_NOT_FOUND")
    user = db.get(User, student.user_id)
    return StudentOut(
        id=str(student.id), name=user.name, email=user.email, roll_number=student.roll_number,
        department=student.department, branch=student.branch, year=student.year,
        semester=student.semester, section=student.section, admission_year=student.admission_year,
    )


# ---------------------------------------------------------------------- faculty
@router.get("/faculty", response_model=list[FacultyOut], dependencies=[AdminDeps])
def list_faculty(db: Session = Depends(get_db)):
    from app.models import Faculty

    rows = db.query(Faculty, User).join(User, Faculty.user_id == User.id).all()
    return [
        FacultyOut(
            id=str(f.id), name=u.name, email=u.email, employee_id=f.employee_id,
            department=f.department, designation=f.designation,
            course_ids=[str(c.id) for c in f.courses],
        )
        for f, u in rows
    ]


@router.post("/faculty", response_model=FacultyOut, status_code=201, dependencies=[AdminDeps])
def create_faculty(payload: FacultyCreate, db: Session = Depends(get_db)):
    user = auth_service.create_faculty(
        db,
        name=payload.name, email=payload.email, password=payload.password,
        employee_id=payload.employee_id, department=payload.department,
        designation=payload.designation, course_ids=payload.course_ids,
    )
    from app.models import Faculty

    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    return FacultyOut(
        id=str(faculty.id), name=user.name, email=user.email, employee_id=faculty.employee_id,
        department=faculty.department, designation=faculty.designation,
        course_ids=[str(c.id) for c in faculty.courses],
    )


@router.patch("/faculty/{faculty_id}", response_model=FacultyOut, dependencies=[AdminDeps])
def update_faculty(faculty_id: uuid.UUID, payload: FacultyUpdate, db: Session = Depends(get_db)):
    from app.models import Faculty

    faculty = db.get(Faculty, faculty_id)
    if faculty is None:
        raise NotFoundError("Faculty could not be found.", code="FACULTY_NOT_FOUND")
    data = payload.model_dump(exclude_unset=True)
    if "course_ids" in data:
        course_ids = data.pop("course_ids") or []
        faculty.courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
    for field, value in data.items():
        setattr(faculty, field, value)
    if "is_active" in data:
        user = db.get(User, faculty.user_id)
        user.is_active = data["is_active"]
    db.commit()
    db.refresh(faculty)
    user = db.get(User, faculty.user_id)
    return FacultyOut(
        id=str(faculty.id), name=user.name, email=user.email, employee_id=faculty.employee_id,
        department=faculty.department, designation=faculty.designation,
        course_ids=[str(c.id) for c in faculty.courses],
    )
