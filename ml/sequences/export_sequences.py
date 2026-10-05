"""Export temporal sequences aligned with the Phase 1 training dataset.

Produces ml/data/processed/sequences.npz containing:
    sequences  [N, T, F]  raw weekly values (standardization stats stored separately)
    masks      [N, T]
    tabular    [N, K]     raw tabular feature rows (dataset.csv order, incl. student/course id cols)
    y_regression / y_classification
plus sequences_index.json (pair order + split assignment) and sequence_stats.json.

Run from the project root:
    python -m ml.sequences.export_sequences
"""
import json
from datetime import timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from ml.config import (
    DATASET_FILE,
    RISK_SCORE_THRESHOLD,
    SEQUENCE_FEATURES,
    SEQUENCES_FILE,
    SEQUENCES_INDEX_FILE,
    SEQUENCE_STATS_FILE,
)
from ml.sequences.dataset import compute_stats
from ml.sequences.sequence_builder import build_sequence_dataset


def _get_database_url() -> str:
    import os
    from pathlib import Path

    url = os.environ.get("DATABASE_URL")
    if not url:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        raise RuntimeError("DATABASE_URL is not set (env or .env).")
    return url


def export() -> dict:
    from ml.training.train import load_dataset, make_split

    dataset = load_dataset(DATASET_FILE)  # includes student_id, course_id, endterm_percentage
    engine = create_engine(_get_database_url())
    with engine.connect() as conn:
        assessments = pd.read_sql(text("SELECT student_id, course_id, assessment_type, score, maximum_score, assessment_date FROM assessments"), conn)
        attendance = pd.read_sql(text("SELECT student_id, course_id, classes_conducted, classes_attended, date FROM attendance"), conn)
        activities = pd.read_sql(text("SELECT student_id, course_id, activity_date, session_duration, videos_watched, videos_completed, documents_opened, quiz_attempts, assignments_submitted, late_submissions, practice_questions_attempted, login_count FROM learning_activities"), conn)
    for df in (assessments, attendance, activities):
        for col in ("student_id", "course_id"):
            if col in df.columns:
                df[col] = df[col].astype(str)

    # sequence end = week before the ENDTERM (no target leakage into the temporal window)
    assessments["assessment_date"] = pd.to_datetime(assessments["assessment_date"])
    endterm = assessments[assessments["assessment_type"].astype(str).str.upper() == "ENDTERM"]
    end_dates: dict[tuple[str, str], pd.Timestamp] = {}
    for (sid, cid), grp in endterm.groupby(["student_id", "course_id"]):
        end_dates[(sid, cid)] = grp["assessment_date"].min().normalize() - timedelta(days=7)

    pairs = list(zip(dataset["student_id"].astype(str), dataset["course_id"].astype(str)))
    raw_seqs, raw_masks = build_sequence_dataset(assessments, attendance, activities, pd.DataFrame(), pairs, end_dates)

    # right-align variable lengths into [N, T, F]
    T = max(1, max(len(s) for s in raw_seqs))
    F = len(SEQUENCE_FEATURES)
    sequences = np.zeros((len(raw_seqs), T, F), dtype=np.float32)
    masks = np.zeros((len(raw_seqs), T), dtype=np.float32)
    for i, (s, m) in enumerate(zip(raw_seqs, raw_masks)):
        t = len(s)
        sequences[i, T - t:] = s[-T:]
        masks[i, T - t:] = m[-T:]

    # split assignment MUST match Phase 1 train.py: same dataset order + same seed.
    # Recreate the split indices with the same procedure.
    numeric_cols = dataset.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != "endterm_percentage"]
    tabular = dataset[numeric_cols].to_numpy(dtype=np.float32)
    y_reg = dataset["endterm_percentage"].to_numpy(dtype=np.float32)
    y_cls = (dataset["endterm_percentage"].astype(float) < RISK_SCORE_THRESHOLD).astype(np.float32)

    from sklearn.model_selection import train_test_split

    idx = np.arange(len(dataset))
    train_idx, temp_idx = train_test_split(idx, test_size=0.30, random_state=42)
    val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42)

    stats = compute_stats(sequences[train_idx], masks[train_idx])

    np.savez(SEQUENCES_FILE, sequences=sequences, masks=masks, tabular=tabular, y_regression=y_reg, y_classification=y_cls, train_idx=train_idx, val_idx=val_idx, test_idx=test_idx)
    index = {
        "pairs": [[sid, cid] for sid, cid in pairs],
        "feature_columns": numeric_cols,
        "sequence_features": SEQUENCE_FEATURES,
        "splits": {"train": train_idx.tolist(), "validation": val_idx.tolist(), "test": test_idx.tolist()},
    }
    SEQUENCES_INDEX_FILE.write_text(json.dumps(index), encoding="utf-8")
    SEQUENCE_STATS_FILE.write_text(json.dumps(stats), encoding="utf-8")

    print(
        f"Exported {len(pairs)} sequences [T={T}, F={F}] -> {SEQUENCES_FILE} "
        f"(train/val/test = {len(train_idx)}/{len(val_idx)}/{len(test_idx)})"
    )
    return {"n": len(pairs), "T": T, "F": F}


if __name__ == "__main__":
    export()
