"""Sequence builder (§7): converts raw student history into weekly temporal sequences.

One sequence per (student, course):
    [
      [attendance, quiz_avg, assignment_avg, midterm, study_hours, video_completion,
       quiz_attempts, submission_rate, practice, logins, engagement, perf_trend, att_trend],
      ...  # oldest -> newest week
    ]

NaN-heavy leading weeks are masked (mask=0). All configuration lives in ml/config.py.
"""
import numpy as np
import pandas as pd

from ml.config import SEQUENCE_FEATURES, SEQUENCE_LENGTH
from ml.features.engagement import compute_engagement_score

ATTENDANCE_LAG_WEEKS = 4  # monthly attendance rows are forward-filled across ~4 weeks


def _empty_week() -> dict:
    return {f: np.nan for f in SEQUENCE_FEATURES}


def _weekly_grid(start: pd.Timestamp, end: pd.Timestamp, max_weeks: int) -> list[pd.Timestamp]:
    """Week bin END dates covering [start, end], newest last, capped at max_weeks."""
    if end < start:
        end = start
    n_weeks = max(1, int(np.ceil((end - start).days / 7)))
    n_weeks = min(n_weeks, max_weeks)
    # align the last bin to `end` and step backwards
    return [end - pd.Timedelta(days=7 * (n_weeks - 1 - i)) for i in range(n_weeks)]


def build_weekly_sequence(
    assessments: pd.DataFrame,
    attendance: pd.DataFrame,
    activities: pd.DataFrame,
    student_id: str,
    course_id: str,
    end_date: pd.Timestamp,
    expected_assignments: int = 0,
    max_weeks: int = SEQUENCE_LENGTH,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (sequence [T, F] float, mask [T] float) for one (student, course).

    Chronologically sorted (§7). Weeks outside the course's active span are masked out.
    """
    a = (
        assessments[(assessments["student_id"] == student_id) & (assessments["course_id"] == course_id)].copy()
        if "student_id" in assessments.columns
        else assessments.iloc[0:0]
    )
    t = (
        attendance[(attendance["student_id"] == student_id) & (attendance["course_id"] == course_id)].copy()
        if "student_id" in attendance.columns
        else attendance.iloc[0:0]
    )
    act = (
        activities[(activities["student_id"] == student_id) & (activities["course_id"] == course_id)].copy()
        if "student_id" in activities.columns
        else activities.iloc[0:0]
    )

    for df in (a, t, act):
        if not df.empty:
            for col in ("assessment_date", "date", "activity_date"):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    df["_d"] = df[col]

    # course active span: first to last record
    dates = []
    if not a.empty:
        dates.append(a["_d"].min())
        dates.append(a["_d"].max())
    if not t.empty:
        dates.append(t["_d"].min())
        dates.append(t["_d"].max())
    if not act.empty:
        dates.append(act["_d"].min())
        dates.append(act["_d"].max())
    if not dates:
        return np.zeros((0, len(SEQUENCE_FEATURES)), dtype=np.float32), np.zeros((0,), dtype=np.float32)

    start = min(dates)
    grid = _weekly_grid(start, end_date, max_weeks)

    if not a.empty:
        a["assessment_type"] = a["assessment_type"].astype(str).str.upper()
        a["pct"] = a["score"] / a["maximum_score"].replace(0, np.nan) * 100.0

    weeks: list[dict] = []
    prev_att = np.nan
    prev_quiz = np.nan
    for bin_end in grid:
        bin_start = bin_end - pd.Timedelta(days=6)
        row = _empty_week()

        # ---- attendance: forward-filled from the most recent monthly row <= bin_end
        if not t.empty:
            known = t[t["_d"] <= bin_end]
            if not known.empty:
                last = known.sort_values("_d").iloc[-1]
                if last["classes_conducted"] > 0:
                    row["attendance_percentage"] = last["classes_attended"] / last["classes_conducted"] * 100.0

        # ---- assessments recorded within the bin
        if not a.empty:
            in_bin = a[(a["_d"] >= bin_start) & (a["_d"] <= bin_end)]
            for f, a_type in [
                ("quiz_average", "QUIZ"),
                ("assignment_average", "ASSIGNMENT"),
                ("midterm_score", "MIDTERM"),
            ]:
                subset = in_bin[in_bin["assessment_type"] == a_type]["pct"]
                if len(subset):
                    row[f] = float(subset.mean())

        # ---- activities within the bin
        if not act.empty:
            act_bin = act[(act["_d"] >= bin_start) & (act["_d"] <= bin_end)]
            if not act_bin.empty:
                row["session_duration"] = float(act_bin["session_duration"].sum()) / 60.0
                watched = float(act_bin["videos_watched"].sum())
                completed = float(act_bin["videos_completed"].sum())
                if watched > 0:
                    row["video_completion_rate"] = completed / watched
                row["quiz_attempts"] = float(act_bin["quiz_attempts"].sum())
                row["practice_questions"] = float(act_bin["practice_questions_attempted"].sum())
                row["login_frequency"] = float(act_bin["login_count"].sum())
                submitted = float(act_bin["assignments_submitted"].sum())
                if expected_assignments > 0:
                    row["assignment_submission_rate"] = min(1.0, submitted / expected_assignments)

        # ---- carry-forward for sparse weekly signals (chronological smoothing)
        for carry_f in ("attendance_percentage", "quiz_average", "assignment_average", "midterm_score"):
            if pd.isna(row[carry_f]):
                row[carry_f] = np.nan  # filled after the loop from nearest previous known value

        weeks.append(row)

    # carry forward within available history; keep leading NaNs (masked later)
    for f in ("attendance_percentage", "quiz_average", "assignment_average", "midterm_score"):
        last_val = np.nan
        for w in weeks:
            if pd.isna(w[f]):
                w[f] = last_val
            else:
                last_val = w[f]

    # ---- trends (§8): difference to the previous week's value
    for i, w in enumerate(weeks):
        if i == 0:
            w["performance_trend"] = 0.0
            w["attendance_trend"] = 0.0
        else:
            w["performance_trend"] = (
                (w["quiz_average"] - weeks[i - 1]["quiz_average"])
                if not (pd.isna(w["quiz_average"]) or pd.isna(weeks[i - 1]["quiz_average"]))
                else 0.0
            )
            w["attendance_trend"] = (
                (w["attendance_percentage"] - weeks[i - 1]["attendance_percentage"])
                if not (
                    pd.isna(w["attendance_percentage"]) or pd.isna(weeks[i - 1]["attendance_percentage"])
                )
                else 0.0
            )

    # ---- weekly engagement score
    for w in weeks:
        w["engagement_score"] = compute_engagement_score(
            video_completion_rate=None if pd.isna(w["video_completion_rate"]) else w["video_completion_rate"],
            assignment_submission_rate=None if pd.isna(w["assignment_submission_rate"]) else w["assignment_submission_rate"],
            logins_per_week=None if pd.isna(w["login_frequency"]) else w["login_frequency"],
            session_hours_per_week=None if pd.isna(w["session_duration"]) else w["session_duration"],
            quiz_attempts_per_week=None if pd.isna(w["quiz_attempts"]) else w["quiz_attempts"],
            practice_questions_per_week=None if pd.isna(w["practice_questions"]) else w["practice_questions"],
            late_submission_rate=None,
        )

    seq = np.array(
        [[np.nan_to_num(w[f], nan=0.0) for f in SEQUENCE_FEATURES] for w in weeks], dtype=np.float32
    )
    # mask: weeks with any observed signal
    mask = np.array(
        [1.0 if any(not pd.isna(w[f]) for f in SEQUENCE_FEATURES if f != "engagement_score") else 0.0 for w in weeks],
        dtype=np.float32,
    )
    return seq, mask


def build_sequence_dataset(
    assessments: pd.DataFrame,
    attendance: pd.DataFrame,
    activities: pd.DataFrame,
    courses: pd.DataFrame,
    pairs: list[tuple[str, str]],
    end_dates: dict[tuple[str, str], pd.Timestamp] | None = None,
    max_weeks: int = SEQUENCE_LENGTH,
) -> tuple[np.ndarray, np.ndarray]:
    """Sequences + masks for many (student, course) pairs.

    `end_dates`: per-pair sequence end (for training: week before ENDTERM to avoid
    target leakage; for inference: today).
    """
    expected = (
        assessments.assign(assessment_type=assessments["assessment_type"].astype(str).str.upper())
        .query("assessment_type == 'ASSIGNMENT'")
        .groupby("course_id")
        .size()
        .to_dict()
        if not assessments.empty
        else {}
    )

    seqs, masks = [], []
    for sid, cid in pairs:
        end = (end_dates or {}).get((sid, cid), pd.Timestamp.today().normalize())
        s, m = build_weekly_sequence(
            assessments, attendance, activities, sid, cid,
            end_date=end, expected_assignments=int(expected.get(cid, 0)), max_weeks=max_weeks,
        )
        seqs.append(s)
        masks.append(m)
    return seqs, masks
