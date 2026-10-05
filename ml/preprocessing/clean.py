"""Data cleaning applied BEFORE feature engineering (§23).

Handles: invalid values, duplicates, extreme outliers. Missing values and
encoding/scaling are handled by the sklearn pipeline *after* the train/test
split, to avoid leakage.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VALID_ASSESSMENT_TYPES = {"QUIZ", "ASSIGNMENT", "MIDTERM", "ENDTERM", "LAB", "PROJECT", "OTHER"}


@dataclass
class CleaningReport:
    dropped_rows: int = 0
    fixed_values: int = 0
    notes: list[str] = field(default_factory=list)


def clean_assessments(df: pd.DataFrame, report: CleaningReport | None = None) -> pd.DataFrame:
    report = report or CleaningReport()
    if df.empty:
        return df
    before = len(df)
    df = df.copy()
    df["assessment_type"] = df["assessment_type"].astype(str).str.upper()
    df = df[df["assessment_type"].isin(VALID_ASSESSMENT_TYPES)]

    for col in ("score", "maximum_score"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["score", "maximum_score"])
    # score must be within [0, maximum_score]; maximum_score must be positive
    df = df[(df["score"] >= 0) & (df["maximum_score"] > 0) & (df["score"] <= df["maximum_score"] * 1.0)]
    # extreme outlier guard: individual scores above 100% or negative after coercion are dropped
    df = df.drop_duplicates(subset=["student_id", "course_id", "assessment_type", "assessment_date"])

    report.dropped_rows += before - len(df)
    return df


def clean_attendance(df: pd.DataFrame, report: CleaningReport | None = None) -> pd.DataFrame:
    report = report or CleaningReport()
    if df.empty:
        return df
    before = len(df)
    df = df.copy()
    for col in ("classes_conducted", "classes_attended"):
        df[col] = pd.to_numeric(df[col], errors="coerce").clip(lower=0)
    df = df.dropna(subset=["classes_conducted", "classes_attended"])
    invalid = df["classes_attended"] > df["classes_conducted"]
    if invalid.any():
        # fix by capping attended at conducted rather than dropping the whole record
        df.loc[invalid, "classes_attended"] = df.loc[invalid, "classes_conducted"]
        report.fixed_values += int(invalid.sum())
    report.dropped_rows += before - len(df)
    return df


def clean_activities(df: pd.DataFrame, report: CleaningReport | None = None) -> pd.DataFrame:
    report = report or CleaningReport()
    if df.empty:
        return df
    before = len(df)
    df = df.copy()
    counts = [
        "session_duration", "videos_watched", "videos_completed", "documents_opened",
        "quiz_attempts", "assignments_submitted", "late_submissions",
        "practice_questions_attempted", "login_count",
    ]
    for col in counts:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").clip(lower=0).fillna(0)
    if "videos_completed" in df and "videos_watched" in df:
        over = df["videos_completed"] > df["videos_watched"]
        df.loc[over, "videos_completed"] = df.loc[over, "videos_watched"]
        report.fixed_values += int(over.sum())
    if "late_submissions" in df and "assignments_submitted" in df:
        over = df["late_submissions"] > df["assignments_submitted"]
        df.loc[over, "late_submissions"] = df.loc[over, "assignments_submitted"]
        report.fixed_values += int(over.sum())
    report.dropped_rows += before - len(df)
    return df


def clean_students(df: pd.DataFrame, report: CleaningReport | None = None) -> pd.DataFrame:
    report = report or CleaningReport()
    df = df.copy()
    if "department" in df:
        df["department"] = df["department"].fillna("UNKNOWN").astype(str)
    if "branch" in df:
        df["branch"] = df["branch"].fillna("UNKNOWN").astype(str)
    return df


def clip_outliers_iqr(series: pd.Series, factor: float = 3.0) -> pd.Series:
    """Winsorize extreme values beyond factor*IQR (used on derived numeric features if needed)."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - factor * iqr, q3 + factor * iqr
    return series.clip(lower, upper)


def any_nan_percentage(df: pd.DataFrame, column: str = "attendance_percentage") -> bool:
    return bool(df[column].isna().any()) if column in df else bool(np.nan)
