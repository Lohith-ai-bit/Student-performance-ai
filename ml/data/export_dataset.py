"""Export the training dataset from PostgreSQL to CSV.

Run from the project root (with DATABASE_URL set or .env present):
    python -m ml.data.export_dataset

Produces ml/data/processed/dataset.csv with one row per (student, course)
that has a known ENDTERM target.
"""
import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from ml.config import DATASET_FILE, DATA_PROCESSED_DIR
from ml.features.build_features import build_training_dataset
from ml.preprocessing.clean import (
    CleaningReport,
    clean_activities,
    clean_assessments,
    clean_attendance,
    clean_students,
)

TABLE_QUERIES = {
    "assessments": "SELECT student_id, course_id, assessment_type, score, maximum_score, assessment_date FROM assessments",
    "attendance": "SELECT student_id, course_id, classes_conducted, classes_attended, date FROM attendance",
    "activities": "SELECT student_id, course_id, activity_date, session_duration, videos_watched, videos_completed, documents_opened, quiz_attempts, assignments_submitted, late_submissions, practice_questions_attempted, login_count FROM learning_activities",
    "students": "SELECT id, department, branch, year, semester, section, admission_year FROM students",
    "courses": "SELECT id, course_code, course_name, semester FROM courses",
}

# columns the ML layer expects (keep only these so extra DB columns never leak in)
RENAME = {
    "assessments": {"assessment_date": "assessment_date"},
    "attendance": {"date": "date"},
    "activities": {"activity_date": "activity_date"},
}


def _get_database_url(cli_value: str | None) -> str:
    url = cli_value or os.environ.get("DATABASE_URL")
    if not url:
        # try loading the project .env (simple parse; avoids extra dependency)
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        raise RuntimeError("DATABASE_URL is not set (env, --database-url, or .env).")
    return url


def export(database_url: str) -> Path:
    engine = create_engine(database_url)
    frames: dict[str, pd.DataFrame] = {}
    with engine.connect() as conn:
        for name, query in TABLE_QUERIES.items():
            frames[name] = pd.read_sql(text(query), conn)
    for name, df in frames.items():
        # normalize ids to str so groupby/merge behave consistently
        for col in ("student_id", "course_id", "id"):
            if col in df.columns:
                df[col] = df[col].astype(str)

    report = CleaningReport()
    assessments = clean_assessments(frames["assessments"], report)
    attendance = clean_attendance(frames["attendance"], report)
    activities = clean_activities(frames["activities"], report)
    students = clean_students(frames["students"], report)
    courses = frames["courses"]

    X, y = build_training_dataset(assessments, attendance, activities, students, courses)
    X = X.drop(columns=["endterm_percentage"], errors="ignore")
    dataset = X.copy()
    dataset["endterm_percentage"] = y

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(DATASET_FILE, index=True)
    print(
        f"Exported {len(dataset)} training rows "
        f"(cleaning: dropped={report.dropped_rows}, fixed={report.fixed_values}) -> {DATASET_FILE}"
    )
    return DATASET_FILE


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ML training dataset from PostgreSQL")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    export(_get_database_url(args.database_url))


if __name__ == "__main__":
    main()
