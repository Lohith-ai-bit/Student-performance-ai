"""Development-only seed script (§41). ALL DATA IS SYNTHETIC.

Generates a realistic-but-not-manipulated dataset (as of Oct 2026):
- 120 students across 5 departments, year 2, semester 3 (sections A/B)
- Semester 1 (Aug-Dec 2025) and 2 (Jan-May 2026): completed — full assessments
  including ENDTERM (the regression target), attendance, learning activities.
- Semester 3 (Aug-Dec 2026): IN PROGRESS — quizzes/assignments/midterm/lab,
  attendance and activities, no ENDTERM yet (this is what the model predicts).
- Scores correlate with a latent ability + diligence; attendance and engagement
  correlate with diligence — weak natural correlations, no guaranteed outcome.

Run from backend/:
    python -m app.seed              # seed if empty
    python -m app.seed --drop       # wipe all tables first
"""
import argparse
import random
from datetime import date, timedelta

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Assessment, Attendance, Course, Department, Enrollment, Faculty,
    LearningActivity, Prediction, Student, User,
)
from app.models.attendance import compute_attendance_percentage
from app.models.enums import AssessmentType, Role

random.seed(42)

SYNTHETIC_NOTICE = "SYNTHETIC SEED DATA"

DEPARTMENTS = [
    ("Computer Science and Engineering", "CSE"),
    ("Electronics and Communication Engineering", "ECE"),
    ("Mechanical Engineering", "ME"),
    ("Civil Engineering", "CE"),
    ("Information Technology", "IT"),
]

# 7 courses per department: 2 for sem 1, 2 for sem 2, 3 for sem 3 (in progress)
COURSE_TEMPLATES = {
    "CSE": [
        ("CS101", "Programming Fundamentals"), ("CS102", "Discrete Mathematics"),
        ("CS201", "Data Structures"), ("CS202", "Computer Organization"),
        ("CS301", "Operating Systems"), ("CS302", "Database Management Systems"),
        ("CS303", "Software Engineering"),
    ],
    "ECE": [
        ("EC101", "Basic Electronics"), ("EC102", "Network Analysis"),
        ("EC201", "Signals and Systems"), ("EC202", "Electromagnetics"),
        ("EC301", "Digital Signal Processing"), ("EC302", "Communication Systems"),
        ("EC303", "Electronic Circuits"),
    ],
    "ME": [
        ("ME101", "Engineering Mechanics"), ("ME102", "Engineering Graphics"),
        ("ME201", "Thermodynamics"), ("ME202", "Strength of Materials"),
        ("ME301", "Fluid Mechanics"), ("ME302", "Heat Transfer"),
        ("ME303", "Manufacturing Processes"),
    ],
    "CE": [
        ("CE101", "Surveying"), ("CE102", "Engineering Geology"),
        ("CE201", "Structural Analysis"), ("CE202", "Fluid Mechanics"),
        ("CE301", "Geotechnical Engineering"), ("CE302", "Transportation Engineering"),
        ("CE303", "Environmental Engineering"),
    ],
    "IT": [
        ("IT101", "Web Technologies"), ("IT102", "Digital Logic"),
        ("IT201", "Object Oriented Programming"), ("IT202", "Microprocessors"),
        ("IT301", "Computer Graphics"), ("IT302", "Database Systems"),
        ("IT303", "Cloud Computing"),
    ],
}

FIRST_NAMES = ["Aarav", "Diya", "Ishaan", "Meera", "Rohan", "Ananya", "Kabir", "Saanvi", "Arjun", "Priya",
               "Vivaan", "Aditi", "Rahul", "Nisha", "Dev", "Tara", "Kiran", "Zoya", "Aditya", "Riya"]
LAST_NAMES = ["Sharma", "Patel", "Reddy", "Iyer", "Khan", "Gupta", "Nair", "Singh", "Das", "Kulkarni",
              "Mehta", "Rao", "Joshi", "Verma", "Bose"]

# (semester, start_year, start_month, planned_weeks, completed)
SEMESTER_PLAN = [
    (1, 2025, 8, 16, True),
    (2, 2026, 1, 16, True),
    (3, 2026, 8, 9, False),   # in progress as of Oct 2026
]

COMPLETED_ASSESSMENTS = [
    (AssessmentType.QUIZ, 2), (AssessmentType.ASSIGNMENT, 2),
    (AssessmentType.MIDTERM, 1), (AssessmentType.ENDTERM, 1),
]
CURRENT_ASSESSMENTS = [
    (AssessmentType.QUIZ, 3), (AssessmentType.ASSIGNMENT, 2),
    (AssessmentType.MIDTERM, 1), (AssessmentType.LAB, 1),
]


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score(ability: float, diligence: float, attendance_effect: float, noise: float) -> float:
    base = 0.55 * ability + 12.0 * diligence + 10.0 * attendance_effect
    return round(clip(base + random.gauss(0, noise), 5, 100), 1)


def generate() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Database already contains users. Use --drop to reseed.")
            return

        # ---------------------------------------------------------- departments
        departments: dict[str, Department] = {}
        for name, code in DEPARTMENTS:
            dept = Department(name=name, code=code)
            db.add(dept)
            departments[code] = dept
        db.flush()

        # -------------------------------------------------------------- courses
        courses_by_semester: dict[int, list[Course]] = {p[0]: [] for p in SEMESTER_PLAN}
        for dept_code, templates in COURSE_TEMPLATES.items():
            dept = departments[dept_code]
            for i, (course_code, course_name) in enumerate(templates):
                semester = SEMESTER_PLAN[min(i // 2, len(SEMESTER_PLAN) - 1)][0]
                course = Course(
                    course_code=course_code,
                    course_name=course_name,
                    credits=random.choice([3, 4]),
                    department_id=dept.id,
                    semester=semester,
                )
                db.add(course)
                courses_by_semester[semester].append(course)
        db.flush()

        # -------------------------------------------------------------- faculty
        for i, (dept_name, dept_code) in enumerate(DEPARTMENTS, start=1):
            user = User(
                name=f"Prof. {FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 3) % len(LAST_NAMES)]}",
                email=f"faculty{i}@university.edu",
                password_hash=hash_password("Faculty@123"),
                role=Role.FACULTY,
            )
            member = Faculty(
                user=user,
                employee_id=f"F{i:03d}",
                department=dept_name,
                designation=random.choice(["Assistant Professor", "Associate Professor", "Professor"]),
            )
            member.courses = [c for c in sum(courses_by_semester.values(), []) if c.department_id == departments[dept_code].id]
            db.add(user)
            db.add(member)

        admin = User(
            name="System Administrator",
            email="admin@university.edu",
            password_hash=hash_password("Admin@1234"),
            role=Role.ADMIN,
        )
        db.add(admin)

        # ------------------------------------------------------------- students
        students: list[tuple[Student, float, float]] = []
        for i in range(1, 121):
            dept_code = DEPARTMENTS[i % len(DEPARTMENTS)][1]
            user = User(
                name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                email=f"student{i}@university.edu",
                password_hash=hash_password("Student@123"),
                role=Role.STUDENT,
            )
            student = Student(
                user=user,
                roll_number=f"S{i:03d}",
                department=dept_code,
                branch=departments[dept_code].name,
                year=2,
                semester=3,
                section="A" if i % 2 == 1 else "B",
                admission_year=2025,
            )
            ability = clip(random.gauss(62, 14), 25, 96)
            diligence = clip(random.uniform(0.35, 1.0), 0.3, 1.0)
            students.append((student, ability, diligence))
            db.add(user)
            db.add(student)
        db.flush()

        # -------------------------------------------------- per-semester records
        today = date.today()
        for sem, start_year, start_month, weeks, completed in SEMESTER_PLAN:
            start = date(start_year, start_month, 1)
            courses = courses_by_semester[sem]
            for student, ability, diligence in students:
                attendance_propensity = clip(0.45 + 0.5 * diligence + random.gauss(0, 0.08), 0.3, 1.0)
                engagement_propensity = clip(0.30 + 0.6 * diligence + random.gauss(0, 0.10), 0.2, 1.2)
                dept_courses = [c for c in courses if c.department_id == departments[student.department].id]

                for course in dept_courses:
                    db.add(Enrollment(
                        student_id=student.id, course_id=course.id,
                        academic_year=start.year if start_month >= 6 else start.year - 1,
                        semester=sem, enrollment_date=start,
                    ))

                    attendance_effect = (attendance_propensity - 0.65) * 18.0
                    plan = COMPLETED_ASSESSMENTS if completed else CURRENT_ASSESSMENTS
                    for a_type, count in plan:
                        for _ in range(count):
                            max_offset = (weeks * 7 - 10) if completed else max(11, (today - start).days - 2)
                            day = start + timedelta(days=random.randint(10, max_offset))
                            if day > today:
                                day = today - timedelta(days=1)
                            noise = 9.0 if a_type == AssessmentType.ENDTERM else 6.0
                            db.add(Assessment(
                                student_id=student.id, course_id=course.id,
                                assessment_type=a_type,
                                score=score(ability, diligence, attendance_effect, noise),
                                maximum_score=100.0, assessment_date=day,
                            ))

                    # attendance: one row per month elapsed
                    months_elapsed = min(weeks // 4 + 1, max(1, (today - start).days // 30 + 1))
                    for m in range(months_elapsed):
                        month_date = start + timedelta(days=30 * m)
                        if month_date > today:
                            break
                        conducted = random.randint(14, 22)
                        attended = int(round(conducted * clip(attendance_propensity + random.gauss(0, 0.07), 0, 1)))
                        db.add(Attendance(
                            student_id=student.id, course_id=course.id,
                            classes_conducted=conducted, classes_attended=min(attended, conducted),
                            attendance_percentage=compute_attendance_percentage(conducted, attended),
                            date=month_date,
                        ))

                    # learning activities: weekly rows within the semester so far
                    weeks_elapsed = weeks if completed else max(1, (today - start).days // 7)
                    for w in range(weeks_elapsed):
                        day = start + timedelta(days=7 * w + random.randint(0, 6))
                        if day > today:
                            continue
                        intensity = clip(engagement_propensity + random.gauss(0, 0.15), 0.05, 1.2)
                        watched = int(round(6 * intensity))
                        submitted = int(round(2 * clip(intensity + 0.15, 0, 1)))
                        db.add(LearningActivity(
                            student_id=student.id, course_id=course.id, activity_date=day,
                            session_duration=int(round(50 * intensity + random.randint(0, 25))),
                            videos_watched=watched,
                            videos_completed=int(round(watched * clip(intensity + random.gauss(0, 0.10), 0, 1))),
                            documents_opened=int(round(4 * intensity)),
                            quiz_attempts=int(round(2 * intensity)),
                            assignments_submitted=submitted,
                            late_submissions=1 if (submitted and random.random() > 0.75 + 0.2 * diligence) else 0,
                            practice_questions_attempted=int(round(20 * intensity)),
                            login_count=random.randint(2, 6) if intensity > 0.4 else random.randint(0, 2),
                        ))

        db.commit()

        counts = {
            "users": db.query(User).count(),
            "students": db.query(Student).count(),
            "faculty": db.query(Faculty).count(),
            "courses": db.query(Course).count(),
            "assessments": db.query(Assessment).count(),
            "attendance": db.query(Attendance).count(),
            "learning_activities": db.query(LearningActivity).count(),
        }
        print(f"[{SYNTHETIC_NOTICE}] Seed complete: {counts}")
        print("Demo logins:")
        print("  ADMIN    admin@university.edu   / Admin@1234")
        print("  FACULTY  faculty1@university.edu / Faculty@123  (CSE courses)")
        print("  STUDENT  student1@university.edu / Student@123")
    finally:
        db.close()


def drop_all() -> None:
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic development data")
    parser.add_argument("--drop", action="store_true", help="Drop all tables before seeding")
    args = parser.parse_args()
    if args.drop:
        drop_all()
    generate()
