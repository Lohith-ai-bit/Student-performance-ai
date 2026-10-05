"""Live (per-request) sequence construction for Transformer/Hybrid inference."""
import numpy as np
import pandas as pd

from ml.config import SEQUENCE_FEATURES, SEQUENCE_LENGTH, SEQUENCE_STATS_FILE
from ml.sequences.sequence_builder import build_weekly_sequence

EXPECTED_ASSIGNMENTS_BY_COURSE: dict[str, int] = {}


def _expected_assignments(db, course_id) -> int:
    from sqlalchemy import select

    from app.models import Assessment

    if not course_id:
        return 0
    key = str(course_id)
    if key not in EXPECTED_ASSIGNMENTS_BY_COURSE:
        count = (
            db.query(Assessment.id)
            .filter(Assessment.course_id == course_id, Assessment.assessment_type == "ASSIGNMENT")
            .count()
        )
        EXPECTED_ASSIGNMENTS_BY_COURSE[key] = int(count)
    return EXPECTED_ASSIGNMENTS_BY_COURSE[key]


def build_live_sequence(db, student, course_id=None) -> tuple[np.ndarray, np.ndarray, list[tuple[str, str]]]:
    """Build standardized [T, F] sequences + masks for the student's courses.

    Returns (sequences [N, T, F], masks [N, T], pairs) where pairs are the
    (student_id, course_id) each row corresponds to.
    """
    from sqlalchemy import select

    from app.models import Assessment, Attendance, Course, LearningActivity

    sid = student.id
    if course_id is not None:
        course_ids = [course_id]
    else:
        ids: set = set()
        ids |= {c for (c,) in db.query(Assessment.course_id).filter(Assessment.student_id == sid).distinct().all()}
        ids |= {c for (c,) in db.query(Attendance.course_id).filter(Attendance.student_id == sid).distinct().all()}
        ids |= {c for (c,) in db.query(LearningActivity.course_id).filter(LearningActivity.student_id == sid).distinct().all()}
        course_ids = sorted(ids)

    if not course_ids:
        return np.zeros((0, SEQUENCE_LENGTH, len(SEQUENCE_FEATURES)), np.float32), np.zeros((0, SEQUENCE_LENGTH), np.float32), []

    q_assess = select(Assessment.student_id, Assessment.course_id, Assessment.assessment_type, Assessment.score, Assessment.maximum_score, Assessment.assessment_date).where(Assessment.student_id == sid)
    q_att = select(Attendance.student_id, Attendance.course_id, Attendance.classes_conducted, Attendance.classes_attended, Attendance.date).where(Attendance.student_id == sid)
    q_act = select(LearningActivity.student_id, LearningActivity.course_id, LearningActivity.activity_date, LearningActivity.session_duration, LearningActivity.videos_watched, LearningActivity.videos_completed, LearningActivity.documents_opened, LearningActivity.quiz_attempts, LearningActivity.assignments_submitted, LearningActivity.late_submissions, LearningActivity.practice_questions_attempted, LearningActivity.login_count).where(LearningActivity.student_id == sid)

    assessments = pd.read_sql(q_assess, db.bind)
    attendance = pd.read_sql(q_att, db.bind)
    activities = pd.read_sql(q_act, db.bind)
    for df in (assessments, attendance, activities):
        for col in ("student_id", "course_id"):
            if col in df.columns:
                df[col] = df[col].astype(str)

    stats = json.loads(SEQUENCE_STATS_FILE.read_text(encoding="utf-8")) if SEQUENCE_STATS_FILE.exists() else None

    seqs, masks, pairs = [], [], []
    for cid in course_ids:
        s, m = build_weekly_sequence(
            assessments, attendance, activities, str(sid), str(cid),
            end_date=pd.Timestamp.today().normalize(),
            expected_assignments=_expected_assignments(db, cid),
            max_weeks=SEQUENCE_LENGTH,
        )
        seqs.append(s)
        masks.append(m)
        pairs.append((str(sid), str(cid)))

    # right-align into fixed [N, T, F]
    T = SEQUENCE_LENGTH
    F = len(SEQUENCE_FEATURES)
    X = np.zeros((len(seqs), T, F), dtype=np.float32)
    M = np.zeros((len(seqs), T), dtype=np.float32)
    for i, (s, m) in enumerate(zip(seqs, masks)):
        t = min(len(s), T)
        X[i, T - t:] = s[-t:]
        M[i, T - t:] = m[-t:]

    if stats is not None:
        mu = np.array(stats["mean"], dtype=np.float32)
        sd = np.array(stats["std"], dtype=np.float32)
        sd[sd < 1e-8] = 1.0
        X = np.nan_to_num((X - mu) / sd) * M[..., None]

    return X, M, pairs


import json  # noqa: E402
