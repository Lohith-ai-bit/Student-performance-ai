"""Dashboard aggregates for student / faculty / admin views (§13, §16, §18).

Phase 1 loads the relevant tables into pandas and computes the aggregates in
memory — the dataset scale of a capstone makes this fine; Phase 3 can move
these to SQL/materialized views when scale grows.
"""
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, Attendance, Course, Department, Enrollment, Faculty,
    LearningActivity, Prediction, Student,
)
from app.services.feature_service import ACTIVITY_COLUMNS


def _read(db: Session, query, columns: list[str]) -> pd.DataFrame:
    df = pd.read_sql(query, db.bind)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in ("student_id", "course_id", "id"):
        if col in df.columns:
            df[col] = df[col].astype(str)
    return df


def _pct(score, maximum):
    if not maximum or maximum <= 0 or pd.isna(maximum):
        return np.nan
    return float(score) / float(maximum) * 100.0


PERFORMANCE_BUCKETS = [(0, 40, "0-40"), (40, 50, "40-50"), (50, 60, "50-60"), (60, 70, "60-70"), (70, 85, "70-85"), (85, 100.01, "85-100")]
ATTENDANCE_BUCKETS = [(0, 50, "0-50%"), (50, 65, "50-65%"), (65, 75, "65-75%"), (75, 85, "75-85%"), (85, 100.01, "85-100%")]


def _bucketize(values: pd.Series, buckets) -> list[dict]:
    counts = {label: 0 for _, _, label in buckets}
    for v in values.dropna():
        for lo, hi, label in buckets:
            if lo <= float(v) < hi:
                counts[label] += 1
                break
    return [{"bucket": label, "count": c} for label, c in counts.items()]


# --------------------------------------------------------------------- student
def student_dashboard(db: Session, student: Student) -> dict:
    sid = str(student.id)

    assessments = _read(
        db,
        select(Assessment.course_id, Assessment.assessment_type, Assessment.score, Assessment.maximum_score, Assessment.assessment_date).where(Assessment.student_id == student.id),
        ["course_id", "assessment_type", "score", "maximum_score", "assessment_date"],
    )
    attendance = _read(
        db,
        select(Attendance.course_id, Attendance.classes_conducted, Attendance.classes_attended, Attendance.date).where(Attendance.student_id == student.id),
        ["course_id", "classes_conducted", "classes_attended", "date"],
    )
    activities = _read(
        db,
        select(*[getattr(LearningActivity, c) for c in ACTIVITY_COLUMNS]).where(LearningActivity.student_id == student.id),
        ACTIVITY_COLUMNS,
    )
    predictions = _read(
        db,
        select(Prediction.course_id, Prediction.predicted_score, Prediction.risk_probability, Prediction.risk_level, Prediction.prediction_date).where(Prediction.student_id == student.id).order_by(Prediction.prediction_date.desc()),
        ["course_id", "predicted_score", "risk_probability", "risk_level", "prediction_date"],
    )

    # course context (all courses the student has any record in)
    course_ids = sorted(
        set(assessments["course_id"]).union(set(attendance["course_id"])).union(set(activities["course_id"]))
    ) if not (assessments.empty and attendance.empty and activities.empty) else []
    courses = (
        pd.read_sql(select(Course.id, Course.course_code, Course.course_name, Course.semester).where(Course.id.in_([uuid.UUID(c) for c in course_ids])), db.bind)
        if course_ids else pd.DataFrame(columns=["id", "course_code", "course_name", "semester"])
    )
    if not courses.empty:
        courses["id"] = courses["id"].astype(str)
    course_names = {row["id"]: row["course_code"] for _, row in courses.iterrows()}

    # per-course performance
    performance: list[dict] = []
    course_attendance: list[dict] = []
    trend_rows: list[dict] = []

    assessments = assessments.copy()
    if not assessments.empty:
        assessments["pct"] = [
            _pct(s, m) for s, m in zip(assessments["score"], assessments["maximum_score"])
        ]
        assessments["assessment_type"] = assessments["assessment_type"].astype(str).str.upper()

    overall_current, overall_final = [], []
    for cid in course_ids:
        name = course_names.get(cid, str(cid)[:8])
        c_rows = assessments[assessments["course_id"] == cid] if not assessments.empty else pd.DataFrame()
        final_rows = c_rows[c_rows["assessment_type"] == "ENDTERM"] if not c_rows.empty else pd.DataFrame()
        current_rows = c_rows[c_rows["assessment_type"] != "ENDTERM"] if not c_rows.empty else pd.DataFrame()
        current_avg = round(float(current_rows["pct"].mean()), 2) if not current_rows.empty else None
        final_avg = round(float(final_rows["pct"].mean()), 2) if not final_rows.empty else None

        if current_avg is not None:
            overall_current.append(current_avg)
        if final_avg is not None:
            overall_final.append(final_avg)

        pred_row = predictions[predictions["course_id"] == cid] if not predictions.empty else pd.DataFrame()
        predicted = float(pred_row.iloc[0]["predicted_score"]) if not pred_row.empty else None

        performance.append(
            {
                "course_id": cid, "course_code": name,
                "current_average": current_avg, "final_average": final_avg,
            }
        )
        trend_rows.append(
            {
                "course_code": name,
                "previous": final_avg,       # completed ENDTERM average (previous performance)
                "current": current_avg,      # in-progress assessment average
                "predicted": predicted,      # latest model prediction
            }
        )

        a_rows = attendance[attendance["course_id"] == cid] if not attendance.empty else pd.DataFrame()
        if not a_rows.empty:
            conducted = float(a_rows["classes_conducted"].sum())
            attended = float(a_rows["classes_attended"].sum())
            pct = round(attended / conducted * 100, 2) if conducted else 0.0
        else:
            conducted = attended = 0
            pct = None
        course_attendance.append(
            {
                "course_id": cid, "course_code": name, "percentage": pct,
                "classes_conducted": int(conducted), "classes_attended": int(attended),
            }
        )

    # GPA on a 10-point scale from completed course ENDTERM averages
    gpa = round(float(np.mean(overall_final)) / 10.0, 2) if overall_final else None
    overall_attendance = None
    if not attendance.empty and attendance["classes_conducted"].sum() > 0:
        overall_attendance = round(
            float(attendance["classes_attended"].sum() / attendance["classes_conducted"].sum() * 100), 2
        )

    # engagement across current activities
    engagement = None
    if not activities.empty:
        try:
            from ml.features.engagement import compute_engagement_score

            weeks = max(
                1.0,
                (
                    pd.to_datetime(activities["activity_date"]).max()
                    - pd.to_datetime(activities["activity_date"]).min()
                ).days / 7.0,
            )
            watched = float(activities["videos_watched"].sum())
            submitted = float(activities["assignments_submitted"].sum())
            late = float(activities["late_submissions"].sum())
            engagement = compute_engagement_score(
                video_completion_rate=float(activities["videos_completed"].sum()) / watched if watched else None,
                assignment_submission_rate=None,
                logins_per_week=float(activities["login_count"].sum()) / weeks,
                session_hours_per_week=float(activities["session_duration"].sum()) / 60.0 / weeks,
                quiz_attempts_per_week=float(activities["quiz_attempts"].sum()) / weeks,
                practice_questions_per_week=float(activities["practice_questions_attempted"].sum()) / weeks,
                late_submission_rate=late / submitted if submitted else None,
            ) * 100.0
        except Exception:
            engagement = None

    latest = predictions.iloc[0].to_dict() if not predictions.empty else None

    return {
        "student": {
            "id": str(student.id), "name": None,  # filled by the route from the User
            "roll_number": student.roll_number, "department": student.department,
            "branch": student.branch, "year": student.year, "semester": student.semester,
            "section": student.section,
        },
        "summary": {
            "gpa": gpa,
            "predicted_score": float(latest["predicted_score"]) if latest else None,
            "attendance_percentage": overall_attendance,
            "engagement_score": round(engagement, 1) if engagement is not None else None,
            "risk_level": latest["risk_level"] if latest else None,
        },
        "performance": performance,
        "performance_trend": trend_rows,
        "attendance": course_attendance,
        "latest_prediction": latest,
    }


# --------------------------------------------------------------------- faculty
def faculty_dashboard(db: Session, faculty: Faculty) -> dict:
    course_ids = [c.id for c in faculty.courses]

    base_filters = []
    if course_ids:
        base_filters.append(Course.id.in_(course_ids))

    assessments = _read(
        db,
        select(Assessment.course_id, Assessment.student_id, Assessment.assessment_type, Assessment.score, Assessment.maximum_score).where(
            Assessment.course_id.in_(course_ids) if course_ids else Assessment.course_id.is_(None)
        ),
        ["course_id", "student_id", "assessment_type", "score", "maximum_score"],
    )
    attendance = _read(
        db,
        select(Attendance.course_id, Attendance.student_id, Attendance.classes_conducted, Attendance.classes_attended).where(
            Attendance.course_id.in_(course_ids) if course_ids else Attendance.course_id.is_(None)
        ),
        ["course_id", "student_id", "classes_conducted", "classes_attended"],
    )
    predictions = _read(
        db,
        select(Prediction.student_id, Prediction.predicted_score, Prediction.risk_level, Prediction.prediction_date).where(
            Prediction.course_id.in_(course_ids) if course_ids else Prediction.course_id.is_(None)
        ).order_by(Prediction.prediction_date.desc()),
        ["student_id", "predicted_score", "risk_level", "prediction_date"],
    )

    students = (
        pd.read_sql(
            select(Student.id, Student.roll_number).where(
                Student.id.in_(
                    select(Enrollment.student_id).where(Enrollment.course_id.in_(course_ids))
                )
                if course_ids
                else Student.id.is_(None)
            ),
            db.bind,
        )
        if course_ids
        else pd.DataFrame(columns=["id", "roll_number"])
    )
    if not students.empty:
        students["id"] = students["id"].astype(str)

    current_avg = None
    if not assessments.empty:
        a = assessments.copy()
        a["assessment_type"] = a["assessment_type"].astype(str).str.upper()
        a = a[a["assessment_type"] != "ENDTERM"]
        a["pct"] = [_pct(s, m) for s, m in zip(a["score"], a["maximum_score"])]
        current_avg = round(float(a["pct"].mean()), 2) if not a.empty else None

    avg_attendance = None
    if not attendance.empty and attendance["classes_conducted"].sum() > 0:
        per_pair = attendance.groupby(["student_id", "course_id"]).apply(
            lambda g: g["classes_attended"].sum() / max(1.0, g["classes_conducted"].sum()) * 100.0,
            include_groups=False,
        )
        avg_attendance = round(float(per_pair.mean()), 2)

    # latest prediction per student
    latest_per_student = predictions.drop_duplicates(subset=["student_id"], keep="first") if not predictions.empty else predictions

    risk_counts = (
        latest_per_student["risk_level"].value_counts().to_dict() if not latest_per_student.empty else {}
    )

    performance_values = pd.Series(dtype=float)
    if not assessments.empty:
        a = assessments.copy()
        a["assessment_type"] = a["assessment_type"].astype(str).str.upper()
        a = a[a["assessment_type"] != "ENDTERM"]
        a["pct"] = [_pct(s, m) for s, m in zip(a["score"], a["maximum_score"])]
        performance_values = a.groupby("student_id")["pct"].mean()

    attendance_values = pd.Series(dtype=float)
    if not attendance.empty and attendance["classes_conducted"].sum() > 0:
        attendance_values = attendance.groupby(["student_id"]).apply(
            lambda g: g["classes_attended"].sum() / max(1.0, g["classes_conducted"].sum()) * 100.0,
            include_groups=False,
        )

    return {
        "totals": {
            "students": int(len(students)),
            "avg_performance": current_avg,
            "avg_attendance": avg_attendance,
            "high_risk": int(risk_counts.get("HIGH", 0)),
            "critical_risk": int(risk_counts.get("CRITICAL", 0)),
            "medium_risk": int(risk_counts.get("MEDIUM", 0)),
            "low_risk": int(risk_counts.get("LOW", 0)),
        },
        "performance_distribution": _bucketize(performance_values, PERFORMANCE_BUCKETS),
        "risk_distribution": [
            {"level": lvl, "count": int(risk_counts.get(lvl, 0))}
            for lvl in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        ],
        "attendance_distribution": _bucketize(attendance_values, ATTENDANCE_BUCKETS),
    }


# ----------------------------------------------------------------------- admin
def admin_dashboard(db: Session) -> dict:
    assessments = _read(
        db,
        select(Assessment.student_id, Assessment.course_id, Assessment.assessment_type, Assessment.score, Assessment.maximum_score),
        ["student_id", "course_id", "assessment_type", "score", "maximum_score"],
    )
    attendance = _read(
        db,
        select(Attendance.student_id, Attendance.classes_conducted, Attendance.classes_attended),
        ["student_id", "classes_conducted", "classes_attended"],
    )
    predictions = _read(
        db,
        select(Prediction.student_id, Prediction.risk_level, Prediction.prediction_date).order_by(
            Prediction.prediction_date.desc()
        ),
        ["student_id", "risk_level", "prediction_date"],
    )

    students = pd.read_sql(
        select(Student.id, Student.department, Student.year, Student.branch), db.bind
    )
    faculty_count = db.query(Faculty.id).count()
    course_count = db.query(Course.id).count()
    department_count = db.query(Department.id).count()

    if not students.empty:
        students["id"] = students["id"].astype(str)

    # performance per student (current, non-ENDTERM assessments)
    perf_by_student = pd.Series(dtype=float)
    if not assessments.empty:
        a = assessments.copy()
        a["assessment_type"] = a["assessment_type"].astype(str).str.upper()
        a = a[a["assessment_type"] != "ENDTERM"]
        a["pct"] = [_pct(s, m) for s, m in zip(a["score"], a["maximum_score"])]
        perf_by_student = a.groupby("course_id")["pct"].mean()  # per course offering
        # recompute per student too
        perf_by_student_s = a.groupby("student_id")["pct"].mean() if "student_id" in a else pd.Series(dtype=float)
    else:
        perf_by_student_s = pd.Series(dtype=float)

    avg_performance = round(float(perf_by_student_s.mean()), 2) if not perf_by_student_s.empty else None

    latest_per_student = predictions.drop_duplicates(subset=["student_id"], keep="first") if not predictions.empty else predictions
    risk_counts = latest_per_student["risk_level"].value_counts().to_dict() if not latest_per_student.empty else {}

    # department-level performance
    dept_performance: list[dict] = []
    year_performance: list[dict] = []
    if not students.empty and not perf_by_student_s.empty:
        merged = perf_by_student_s.rename("avg_pct").reset_index().merge(students, left_on="student_id", right_on="id", how="inner")
        for dept, grp in merged.groupby("department"):
            dept_performance.append({"department": dept, "avg_performance": round(float(grp["avg_pct"].mean()), 2)})
        for yr, grp in merged.groupby("year"):
            year_performance.append({"year": f"Year {yr}", "avg_performance": round(float(grp["avg_pct"].mean()), 2)})

    attendance_values = pd.Series(dtype=float)
    if not attendance.empty and attendance["classes_conducted"].sum() > 0:
        attendance_values = attendance.groupby("student_id").apply(
            lambda g: g["classes_attended"].sum() / max(1.0, g["classes_conducted"].sum()) * 100.0,
            include_groups=False,
        )

    return {
        "totals": {
            "students": int(len(students)),
            "faculty": int(faculty_count),
            "courses": int(course_count),
            "departments": int(department_count),
            "avg_performance": avg_performance,
            "at_risk": int(
                risk_counts.get("MEDIUM", 0) + risk_counts.get("HIGH", 0) + risk_counts.get("CRITICAL", 0)
            ),
        },
        "performance_by_department": dept_performance,
        "risk_distribution": [
            {"level": lvl, "count": int(risk_counts.get(lvl, 0))}
            for lvl in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        ],
        "attendance_distribution": _bucketize(attendance_values, ATTENDANCE_BUCKETS),
        "year_wise_performance": year_performance,
    }
