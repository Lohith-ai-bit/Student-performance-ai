"""Feature engineering: raw academic/attendance/behaviour records -> model features.

Contract: operates on pandas DataFrames with the same column names as the
database tables (minus ids/timestamps), so the same code builds the training
dataset (from an export) and serves single-student inference (from live rows).

Feature groups (§21/§22):
  Academic   : quiz/assignment/midterm/lab/project averages, assessment count, score trend
  Attendance : overall percentage, attendance trend
  Behaviour  : per-week rates, video completion, submission rates, engagement score
  Context    : department, branch, course semester, admission year, previous GPA
"""
import numpy as np
import pandas as pd

from ml.features.engagement import compute_engagement_score

EXCLUDED_FROM_TREND = {"ENDTERM"}

FEATURE_COLUMNS_NUMERIC = [
    "quiz_average",
    "assignment_average",
    "midterm_score",
    "lab_average",
    "project_average",
    "assessment_count",
    "score_trend",
    "attendance_percentage",
    "attendance_trend",
    "logins_per_week",
    "session_hours_per_week",
    "documents_per_week",
    "quiz_attempts_per_week",
    "practice_questions_per_week",
    "videos_watched_per_week",
    "video_completion_rate",
    "assignments_submitted_per_week",
    "assignment_submission_rate",
    "late_submission_rate",
    "engagement_score",
    "previous_gpa",
    "course_semester",
    "admission_year",
]

FEATURE_COLUMNS_CATEGORICAL = ["department", "branch"]

FEATURE_COLUMNS = FEATURE_COLUMNS_NUMERIC + FEATURE_COLUMNS_CATEGORICAL

TARGET_COLUMN = "endterm_percentage"


def _empty_assessments() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["student_id", "course_id", "assessment_type", "score", "maximum_score", "assessment_date"]
    )


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else np.nan


def _assessment_features(assessments: pd.DataFrame) -> pd.DataFrame:
    """Per (student, course) aggregates from assessments. ENDTERM is held out as target."""
    if assessments.empty:
        return pd.DataFrame(
            columns=[
                "student_id", "course_id", "quiz_average", "assignment_average", "midterm_score",
                "lab_average", "project_average", "assessment_count", "score_trend", TARGET_COLUMN,
            ]
        )
    df = assessments.copy()
    df["assessment_type"] = df["assessment_type"].astype(str).str.upper()
    df["assessment_date"] = pd.to_datetime(df["assessment_date"])
    max_score = df["maximum_score"].replace(0, np.nan)
    df["pct"] = df["score"] / max_score * 100.0

    rows: list[dict] = []
    for (sid, cid), grp in df.groupby(["student_id", "course_id"], sort=False):
        per_type = grp.groupby("assessment_type")["pct"].mean()

        def avg(t: str) -> float:
            return round(float(per_type[t]), 4) if t in per_type else np.nan

        non_final = grp[~grp["assessment_type"].isin(EXCLUDED_FROM_TREND)].sort_values("assessment_date")
        trend = 0.0
        if len(non_final) >= 4:
            recent = non_final["pct"].tail(3).mean()
            earlier = non_final["pct"].iloc[:-3].mean()
            trend = float(recent - earlier)
        endterm = grp[grp["assessment_type"] == "ENDTERM"]["pct"]

        rows.append(
            {
                "student_id": sid,
                "course_id": cid,
                "quiz_average": avg("QUIZ"),
                "assignment_average": avg("ASSIGNMENT"),
                "midterm_score": avg("MIDTERM"),
                "lab_average": avg("LAB"),
                "project_average": avg("PROJECT"),
                "assessment_count": int(len(non_final)),
                "score_trend": round(trend, 4),
                TARGET_COLUMN: round(float(endterm.mean()), 4) if len(endterm) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _attendance_features(attendance: pd.DataFrame) -> pd.DataFrame:
    if attendance.empty:
        return pd.DataFrame(columns=["student_id", "course_id", "attendance_percentage", "attendance_trend"])
    df = attendance.copy()
    df["date"] = pd.to_datetime(df["date"])

    rows: list[dict] = []
    for (sid, cid), grp in df.groupby(["student_id", "course_id"], sort=False):
        conducted = float(grp["classes_conducted"].sum())
        attended = float(grp["classes_attended"].sum())
        overall = round(attended / conducted * 100.0, 4) if conducted > 0 else np.nan

        trend = 0.0
        if len(grp) >= 4:
            ordered = grp.sort_values("date")
            pct = (
                ordered["classes_attended"] / ordered["classes_conducted"].replace(0, np.nan) * 100.0
            ).dropna()
            if len(pct) >= 4:
                half = len(pct) // 2
                trend = float(pct.iloc[half:].mean() - pct.iloc[:half].mean())

        rows.append(
            {
                "student_id": sid,
                "course_id": cid,
                "attendance_percentage": overall,
                "attendance_trend": round(trend, 4),
            }
        )
    return pd.DataFrame(rows)


ACTIVITY_SUM_COLUMNS = [
    "session_duration", "videos_watched", "videos_completed", "documents_opened",
    "quiz_attempts", "assignments_submitted", "late_submissions",
    "practice_questions_attempted", "login_count",
]


def _activity_features(activities: pd.DataFrame) -> pd.DataFrame:
    if activities.empty:
        return pd.DataFrame(columns=["student_id", "course_id"] + ACTIVITY_SUM_COLUMNS + ["weeks_span"])
    df = activities.copy()
    df["activity_date"] = pd.to_datetime(df["activity_date"])

    rows: list[dict] = []
    for (sid, cid), grp in df.groupby(["student_id", "course_id"], sort=False):
        span_days = (grp["activity_date"].max() - grp["activity_date"].min()).days
        weeks = max(1.0, span_days / 7.0)
        row: dict = {"student_id": sid, "course_id": cid, "weeks_span": weeks}
        for col in ACTIVITY_SUM_COLUMNS:
            row[col] = float(grp[col].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def _previous_gpa(assessments: pd.DataFrame, courses: pd.DataFrame) -> pd.DataFrame:
    """Per (student, course): mean ENDTERM percentage over the student's courses in
    semesters BEFORE that course's semester (GPA on a 10-point scale)."""
    if assessments.empty:
        return pd.DataFrame(columns=["student_id", "course_id", "previous_gpa"])
    df = assessments.copy()
    df["assessment_type"] = df["assessment_type"].astype(str).str.upper()
    max_score = df["maximum_score"].replace(0, np.nan)
    df["pct"] = df["score"] / max_score * 100.0
    endterm = df[df["assessment_type"] == "ENDTERM"].copy()

    course_sem = courses.set_index("id")["semester"].to_dict() if not courses.empty else {}
    endterm["course_sem"] = endterm["course_id"].map(course_sem).astype(float)

    by_student = {sid: grp for sid, grp in endterm.groupby("student_id", sort=False)}
    rows: list[dict] = []
    for sid in endterm["student_id"].unique():
        student_rows = by_student[sid]
        for cid, grp in student_rows.groupby("course_id", sort=False):
            current_sem = grp["course_sem"].iloc[0]
            if pd.isna(current_sem):
                continue
            earlier = student_rows[student_rows["course_sem"] < current_sem]
            rows.append(
                {
                    "student_id": sid,
                    "course_id": cid,
                    "previous_gpa": round(float(earlier["pct"].mean()) / 10.0, 4) if len(earlier) else np.nan,
                }
            )
    return pd.DataFrame(rows, columns=["student_id", "course_id", "previous_gpa"])


def build_features(
    assessments: pd.DataFrame | None,
    attendance: pd.DataFrame | None,
    activities: pd.DataFrame | None,
    students: pd.DataFrame,
    courses: pd.DataFrame,
    course_wide_assessments: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one feature row per (student_id, course_id) present in the raw inputs.

    `course_wide_assessments` should contain assessments of ALL students of the course
    (used only to estimate the number of expected assignments for submission rate).
    """
    assessments = assessments if assessments is not None else _empty_assessments()
    attendance = attendance if attendance is not None else pd.DataFrame()
    activities = activities if activities is not None else pd.DataFrame()
    course_wide = course_wide_assessments if course_wide_assessments is not None else assessments

    a_feats = _assessment_features(assessments)
    t_feats = _attendance_features(attendance)
    act_feats = _activity_features(activities)
    gpa_feats = _previous_gpa(assessments, courses)

    features = (
        a_feats.merge(t_feats, on=["student_id", "course_id"], how="outer")
        .merge(act_feats, on=["student_id", "course_id"], how="outer")
        .merge(gpa_feats, on=["student_id", "course_id"], how="outer")
    )

    # Course offering context: expected assignments (course-wide ASSIGNMENT count).
    cw = course_wide.copy()
    if not cw.empty and "assessment_type" in cw.columns:
        cw["assessment_type"] = cw["assessment_type"].astype(str).str.upper()
        expected = (
            cw[cw["assessment_type"] == "ASSIGNMENT"].groupby("course_id").size().rename("expected_assignments")
        )
        features = features.merge(expected, on="course_id", how="left")
    else:
        features["expected_assignments"] = np.nan
    features["assignment_submission_rate"] = (
        (features["assignments_submitted"] / features["expected_assignments"].replace(0, np.nan))
        .clip(upper=1.0)
    )

    # Per-week behaviour rates
    weeks = features["weeks_span"].fillna(1.0).clip(lower=1.0)
    for src, dst in [
        ("login_count", "logins_per_week"),
        ("quiz_attempts", "quiz_attempts_per_week"),
        ("practice_questions_attempted", "practice_questions_per_week"),
        ("videos_watched", "videos_watched_per_week"),
        ("assignments_submitted", "assignments_submitted_per_week"),
        ("session_duration", "session_hours_per_week"),
        ("documents_opened", "documents_per_week"),
    ]:
        if src in features:
            divisor = 60.0 if dst == "session_hours_per_week" else 1.0
            features[dst] = features[src] / weeks / divisor

    features["video_completion_rate"] = features.apply(
        lambda r: _safe_div(r["videos_completed"], r["videos_watched"]) if r["videos_watched"] else np.nan, axis=1
    )
    features["late_submission_rate"] = features.apply(
        lambda r: _safe_div(r["late_submissions"], r["assignments_submitted"]) if r["assignments_submitted"] else np.nan,
        axis=1,
    )

    features["engagement_score"] = features.apply(
        lambda r: compute_engagement_score(
            video_completion_rate=r["video_completion_rate"] if not pd.isna(r["video_completion_rate"]) else None,
            assignment_submission_rate=(
                r["assignment_submission_rate"] if not pd.isna(r["assignment_submission_rate"]) else None
            ),
            logins_per_week=r["logins_per_week"] if not pd.isna(r["logins_per_week"]) else None,
            session_hours_per_week=(
                r["session_hours_per_week"] if not pd.isna(r["session_hours_per_week"]) else None
            ),
            quiz_attempts_per_week=(
                r["quiz_attempts_per_week"] if not pd.isna(r["quiz_attempts_per_week"]) else None
            ),
            practice_questions_per_week=(
                r["practice_questions_per_week"] if not pd.isna(r["practice_questions_per_week"]) else None
            ),
            late_submission_rate=(
                r["late_submission_rate"] if not pd.isna(r["late_submission_rate"]) else None
            ),
        ),
        axis=1,
    )

    # Student demographics + course level
    students = students.rename(columns={"id": "student_id"})
    student_cols = ["student_id", "department", "branch", "admission_year"]
    features = features.merge(students[student_cols], on="student_id", how="left")
    courses = courses.rename(columns={"id": "course_id", "semester": "course_semester"})
    features = features.merge(courses[["course_id", "course_semester"]], on="course_id", how="left")

    # Final column order (categorical -> string, numeric stays float)
    for col in FEATURE_COLUMNS_CATEGORICAL:
        features[col] = features[col].fillna("UNKNOWN").astype(str)

    features = features.drop_duplicates(subset=["student_id", "course_id"], keep="last")
    features = features.set_index(["student_id", "course_id"])
    return features


def build_training_dataset(
    assessments: pd.DataFrame,
    attendance: pd.DataFrame,
    activities: pd.DataFrame,
    students: pd.DataFrame,
    courses: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Feature matrix + regression target. Rows without ENDTERM (in-progress) are dropped."""
    features = build_features(assessments, attendance, activities, students, courses)
    dataset = features.dropna(subset=[TARGET_COLUMN])
    X = dataset[FEATURE_COLUMNS].copy()
    y = dataset[TARGET_COLUMN].copy()
    X["endterm_percentage"] = y  # kept for classification label derivation by caller
    return X, y
