"""Model training pipeline (§26).

Flow: load -> validate -> split (70/15/15, seeded) -> preprocess (inside pipeline,
fitted on train only) -> train -> validate (model selection) -> evaluate (test)
-> save best model + metadata + experiment tables.

Run from the project root:
    python -m ml.training.train --dataset ml/data/processed/dataset.csv
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.config import (
    ARTIFACTS_DIR,
    DATASET_VERSION,
    EXPERIMENTS_CLASSIFICATION_FILE,
    EXPERIMENTS_REGRESSION_FILE,
    FEATURE_VERSION,
    METADATA_FILE,
    MODEL_CLASSIFICATION_FILE,
    MODEL_REGRESSION_FILE,
    RANDOM_SEED,
    RISK_SCORE_THRESHOLD,
)
from ml.evaluation.metrics import classification_metrics, regression_metrics
from ml.models.factory import get_classification_models, get_regression_models
from ml.preprocessing.pipeline import build_preprocessor
from ml.features.build_features import TARGET_COLUMN

REQUIRED_COLUMNS = ["student_id", "course_id", TARGET_COLUMN]


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run `python -m ml.data.export_dataset` first."
        )
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    df = df.dropna(subset=[TARGET_COLUMN])
    if len(df) < 30:
        raise ValueError(f"Dataset too small for meaningful training ({len(df)} rows).")
    return df


def make_split(X: pd.DataFrame, y: pd.Series, stratify=None, seed: int = RANDOM_SEED):
    """70% train / 15% validation / 15% test, reproducible. Stratification optional."""
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=seed, stratify=stratify
    )
    strat_temp = stratify.loc[y_temp.index] if stratify is not None else None
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=seed, stratify=strat_temp
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def _pipeline(estimator) -> Pipeline:
    return Pipeline([("preprocessor", build_preprocessor()), ("model", estimator)])


def train_all_tasks(df: pd.DataFrame) -> dict:
    X = df.drop(columns=["endterm_percentage", "student_id", "course_id"], errors="ignore")

    # ------------------------------------------------------------------ regression
    y_reg = df[TARGET_COLUMN].astype(float)
    X_tr, X_val, X_te, y_tr, y_val, y_te = make_split(X, y_reg)

    reg_results, reg_fitted = [], {}
    for name, model in get_regression_models().items():
        pipe = _pipeline(model)
        pipe.fit(X_tr, y_tr)
        val_pred = pipe.predict(X_val)
        val_metrics = regression_metrics(y_val, val_pred)
        reg_results.append({"model_name": name, "task": "regression", "validation": val_metrics})
        reg_fitted[name] = (pipe, val_metrics)

    best_reg_name = min(reg_results, key=lambda r: r["validation"]["RMSE"])["model_name"]
    best_reg_pipe, best_reg_val = reg_fitted[best_reg_name]
    best_reg_test = regression_metrics(y_te, best_reg_pipe.predict(X_te))

    # -------------------------------------------------------------- classification
    y_bin = (df[TARGET_COLUMN].astype(float) < RISK_SCORE_THRESHOLD).astype(int)
    Xb_tr, Xb_val, Xb_te, yb_tr, yb_val, yb_te = make_split(X, y_bin, stratify=y_bin)

    cls_results, cls_fitted = [], {}
    for name, model in get_classification_models().items():
        pipe = _pipeline(model)
        pipe.fit(Xb_tr, yb_tr)
        val_pred = pipe.predict(Xb_val)
        val_proba = pipe.predict_proba(Xb_val)[:, 1] if hasattr(pipe, "predict_proba") else None
        val_metrics = classification_metrics(yb_val, val_pred, val_proba)
        cls_results.append({"model_name": name, "task": "classification", "validation": val_metrics})
        cls_fitted[name] = (pipe, val_metrics)

    best_cls_name = max(cls_results, key=lambda r: r["validation"]["F1"])["model_name"]
    best_cls_pipe, best_cls_val = cls_fitted[best_cls_name]
    cls_proba_te = best_cls_pipe.predict_proba(Xb_te)[:, 1] if hasattr(best_cls_pipe, "predict_proba") else None
    best_cls_test = classification_metrics(yb_te, best_cls_pipe.predict(Xb_te), cls_proba_te)

    return {
        "regression": {
            "experiments": reg_results,
            "best_name": best_reg_name,
            "best_pipeline": best_reg_pipe,
            "best_validation": best_reg_val,
            "best_test": best_reg_test,
            "split_sizes": {"train": len(X_tr), "validation": len(X_val), "test": len(X_te)},
        },
        "classification": {
            "experiments": cls_results,
            "best_name": best_cls_name,
            "best_pipeline": best_cls_pipe,
            "best_validation": best_cls_val,
            "best_test": best_cls_test,
            "split_sizes": {"train": len(Xb_tr), "validation": len(Xb_val), "test": len(Xb_te)},
            "risk_threshold": RISK_SCORE_THRESHOLD,
        },
    }


def run(dataset_path: Path, model_version: str = "1.0", dataset_version: str = DATASET_VERSION) -> dict:
    df = load_dataset(dataset_path)
    results = train_all_tasks(df)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(results["regression"]["best_pipeline"], MODEL_REGRESSION_FILE)
    joblib.dump(results["classification"]["best_pipeline"], MODEL_CLASSIFICATION_FILE)

    experiments_reg = pd.DataFrame(results["regression"]["experiments"])
    experiments_cls = pd.DataFrame(results["classification"]["experiments"])
    experiments_reg.to_csv(EXPERIMENTS_REGRESSION_FILE, index=False)
    experiments_cls.to_csv(EXPERIMENTS_CLASSIFICATION_FILE, index=False)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset_version,
        "dataset_rows": int(len(df)),
        "dataset_path": str(dataset_path),
        "feature_version": FEATURE_VERSION,
        "random_seed": RANDOM_SEED,
        "risk_score_threshold": RISK_SCORE_THRESHOLD,
        "models": {
            "regression": {
                "model_name": results["regression"]["best_name"],
                "model_version": model_version,
                "validation_metrics": results["regression"]["best_validation"],
                "test_metrics": results["regression"]["best_test"],
                "split_sizes": results["regression"]["split_sizes"],
                "all_validation_results": results["regression"]["experiments"],
            },
            "classification": {
                "model_name": results["classification"]["best_name"],
                "model_version": model_version,
                "validation_metrics": results["classification"]["best_validation"],
                "test_metrics": results["classification"]["best_test"],
                "split_sizes": results["classification"]["split_sizes"],
                "risk_threshold": RISK_SCORE_THRESHOLD,
                "all_validation_results": results["classification"]["experiments"],
            },
        },
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train baseline performance-prediction models")
    parser.add_argument("--dataset", type=Path, default=None, help="Path to dataset CSV")
    parser.add_argument("--model-version", default="1.0")
    parser.add_argument("--dataset-version", default=DATASET_VERSION)
    args = parser.parse_args()

    from ml.config import DATASET_FILE

    path = args.dataset or DATASET_FILE
    print(f"Training on dataset: {path}")
    metadata = run(path, args.model_version, args.dataset_version)

    print("\n=== Model selection (validation set) ===")
    for task in ("regression", "classification"):
        best = metadata["models"][task]
        print(f"\n[{task}] BEST: {best['model_name']}")
        for row in best["all_validation_results"]:
            print(f"  {row['model_name']:<20} {row['validation']}")
        print(f"  test metrics: {best['test_metrics']}")
    print(f"\nArtifacts saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
