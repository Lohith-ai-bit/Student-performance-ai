"""Feature construction from live database rows for a single student (optionally one course).

Fetches raw records with SQLAlchemy, converts to DataFrames and reuses the exact
same ml.features.build_features code path as offline training — no drift.
"""
import uuid

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assessment, Attendance, Course, LearningActivity, Student

ACTIVITY_COLUMNS = [
    "student_id", "course_id", "activity_date", "session_duration", "videos_watched",
    "videos_completed", "documents_opened", "quiz_attempts", "assignments_submitted",
    "late_submissions", "practice_questions_attempted", "login_count",
]


def _fetch_frames(
    db: Session,
    student: Student,
    course_id: uuid.UUID | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sid = student.id

    assessments_q = select(
        Assessment.student_id, Assessment.course_id, Assessment.assessment_type,
        Assessment.score, Assessment.maximum_score, Assessment.assessment_date,
    ).where(Assessment.student_id == sid)
    attendance_q = select(
        Attendance.student_id, Attendance.course_id, Attendance.classes_conducted,
        Attendance.classes_attended, Attendance.date,
    ).where(Attendance.student_id == sid)
    activities_q = select(
        *[getattr(LearningActivity, c) for c in ACTIVITY_COLUMNS]
    ).where(LearningActivity.student_id == sid)

    # course-wide assessments: only needed to estimate expected assignments per course
    course_ids_q = db.query(Attendance.course_id).filter(Attendance.student_id == sid)
    if course_id is not None:
        course_ids_q = course_ids_q.filter(Attendance.course_id == course_id)
    enrolled_course_ids = [c for (c,) in course_ids_q.distinct().all()]

    if course_id is not None:
        course_ids = [course_id]
    else:
        ids: set = set(enrolled_course_ids)
        ids |= {c for (c,) in db.query(Assessment.course_id).filter(Assessment.student_id == sid).distinct().all()}
        ids |= {c for (c,) in db.query(LearningActivity.course_id).filter(LearningActivity.student_id == sid).distinct().all()}
        course_ids = sorted(ids)

    course_wide = pd.DataFrame()
    if course_ids:
        course_wide_q = select(
            Assessment.course_id, Assessment.assessment_type
        ).where(Assessment.course_id.in_(course_ids))
        course_wide = pd.read_sql(course_wide_q, db.bind)

    assessments = pd.read_sql(assessments_q, db.bind)
    attendance = pd.read_sql(attendance_q, db.bind)
    activities = pd.read_sql(activities_q, db.bind)

    students = pd.DataFrame(
        [
            {
                "id": str(student.id), "department": student.department, "branch": student.branch,
                "year": student.year, "semester": student.semester, "section": student.section,
                "admission_year": student.admission_year,
            }
        ]
    )

    courses_q = select(Course.id, Course.course_code, Course.course_name, Course.semester)
    if course_ids:
        courses_q = courses_q.where(Course.id.in_(course_ids))
    courses = pd.read_sql(courses_q, db.bind)

    for df in (assessments, attendance, activities, course_wide):
        for col in ("student_id", "course_id"):
            if col in df.columns:
                df[col] = df[col].astype(str)
    for col in ("id", "course_id"):
        if col in courses.columns:
            courses[col] = courses[col].astype(str)
    students["id"] = students["id"].astype(str)

    # NOTE: per-course records are NOT filtered to the target course — groupby in
    # build_features separates courses, and previous_gpa needs the student's full history.
    return assessments, attendance, activities, students, courses, course_wide


def build_student_feature_frame(db: Session, student: Student, course_id: uuid.UUID | None = None) -> pd.DataFrame:
    """One feature row per relevant (student, course) pair, using ml.features.build_features."""
    from ml.features.build_features import build_features

    assessments, attendance, activities, students, courses, course_wide = _fetch_frames(
        db, student, course_id
    )
    features = build_features(assessments, attendance, activities, students, courses, course_wide)
    if features.empty:
        return features
    if course_id is not None:
        features = features[features.index.get_level_values("course_id") == str(course_id)]
    return features
