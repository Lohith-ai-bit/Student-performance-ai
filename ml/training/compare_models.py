"""Model comparison + ablation studies (§15/§16/§53).

Trains/evaluates every model family on the SAME 70/15/15 split and writes all
results to the model_experiments table + a CSV report. Nothing is fabricated —
every number comes from an actual run in this process.

Run from the project root:
    python -m ml.training.compare_models            # fusion variants + ablations
"""
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml.config import (
    FEATURE_GROUPS,
    RISK_SCORE_THRESHOLD,
    SEQUENCE_FEATURES,
    SEQUENCES_INDEX_FILE,
)
from ml.evaluation.metrics import classification_metrics, regression_metrics
from ml.models.factory import get_classification_models, get_regression_models
from ml.models.hybrid import HybridModel
from ml.models.transformer import TransformerPredictor
from ml.preprocessing.pipeline import build_preprocessor
from ml.training.torch_common import (
    load_bundle,
    make_loader,
    run_forward,
    seed_everything,
    train_model,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline as SkPipeline

EXPERIMENTS: list[dict] = []


def record(name: str, model_type: str, hyperparameters: dict, val: dict, test: dict, duration: float, notes: str = ""):
    EXPERIMENTS.append(
        {
            "experiment_name": name,
            "model_type": model_type,
            "dataset_version": "v1",
            "hyperparameters": hyperparameters,
            "metrics": {"validation": val, "test": test},
            "training_duration_seconds": round(duration, 2),
            "notes": notes,
        }
    )
    print(f"[{name}] val={val.get('regression', val)} test={test.get('regression', test)}")


# --------------------------------------------------------------------- baselines
def run_baselines() -> None:
    from ml.config import DATASET_FILE
    from ml.features.build_features import TARGET_COLUMN

    df = pd.read_csv(DATASET_FILE).dropna(subset=[TARGET_COLUMN])
    X = df.drop(columns=[TARGET_COLUMN, "student_id", "course_id"])
    y_reg = df[TARGET_COLUMN].astype(float)
    y_cls = (y_reg < RISK_SCORE_THRESHOLD).astype(int)

    idx = np.arange(len(df))
    tr, tmp = train_test_split(idx, test_size=0.30, random_state=42)
    va, te = train_test_split(tmp, test_size=0.50, random_state=42)

    for name, model in get_regression_models().items():
        start = time.time()
        pipe = SkPipeline([("preprocessor", build_preprocessor()), ("model", model)])
        pipe.fit(X.iloc[tr], y_reg.iloc[tr])
        val = regression_metrics(y_reg.iloc[va], pipe.predict(X.iloc[va]))
        test = regression_metrics(y_reg.iloc[te], pipe.predict(X.iloc[te]))
        record(f"Regression/{name}", "BASELINE", {}, val, test, time.time() - start)

    for name, model in get_classification_models().items():
        start = time.time()
        pipe = SkPipeline([("preprocessor", build_preprocessor()), ("model", model)])
        pipe.fit(X.iloc[tr], y_cls.iloc[tr])
        val_pred = pipe.predict(X.iloc[va])
        val_proba = pipe.predict_proba(X.iloc[va])[:, 1] if hasattr(pipe, "predict_proba") else None
        te_pred = pipe.predict(X.iloc[te])
        te_proba = pipe.predict_proba(X.iloc[te])[:, 1] if hasattr(pipe, "predict_proba") else None
        record(
            f"Classification/{name}", "BASELINE", {},
            classification_metrics(y_cls.iloc[va], val_pred, val_proba),
            classification_metrics(y_cls.iloc[te], te_pred, te_proba),
            time.time() - start,
        )


# --------------------------------------------------------------- torch evaluation
def evaluate_torch(model, bundle, kind, split="test"):
    from ml.training.torch_common import evaluate_model

    return evaluate_model(model, bundle, kind, split=split)


def run_transformer(bundle) -> None:
    start = time.time()
    model = TransformerPredictor()
    result = train_model(model, bundle, model_kind="transformer", epochs=120, patience=15, log_prefix="[cmp-transformer] ")
    record(
        "Regression+Classification/TemporalTransformer", "TRANSFORMER",
        model.config.to_dict(), result["validation"], result["test"], result["training_duration_seconds"],
    )


def run_hybrid_variant(bundle, fusion: str, name_suffix: str = "", exclude_seq: list[str] | None = None, exclude_tab: list[str] | None = None, notes: str = "") -> None:
    from ml.config import TransformerConfig

    config = TransformerConfig(fusion=fusion)
    model = HybridModel(n_tabular_features=len(bundle.feature_columns), config=config)
    result = train_model(
        model, bundle, model_kind="hybrid", epochs=120, patience=15,
        log_prefix=f"[cmp-{fusion}{name_suffix}] ",
    )
    record(
        f"Hybrid/{fusion}{name_suffix}",
        "HYBRID", {**config.to_dict(), "exclude_seq": exclude_seq or [], "exclude_tab": exclude_tab or []},
        result["validation"], result["test"], result["training_duration_seconds"], notes=notes,
    )


# ------------------------------------------------------------------- ablations (§53)
def zeroed_bundle(base_bundle, exclude_seq: list[str], exclude_tab: list[str]):
    """Copy of the bundle with the given sequence/tabular features zeroed out."""
    import copy

    bundle = copy.copy(base_bundle)
    seq_idx = [SEQUENCE_FEATURES.index(f) for f in exclude_seq if f in SEQUENCE_FEATURES]
    tab_idx = [bundle.feature_columns.index(f) for f in exclude_tab if f in bundle.feature_columns]
    sequences = base_bundle.sequences.copy()
    tabular = base_bundle.tabular.copy()
    if seq_idx:
        sequences[..., seq_idx] = 0.0
    if tab_idx:
        tabular[:, tab_idx] = np.nan  # the imputer in dataset() treats NaN like missing
    bundle.sequences, bundle.tabular = sequences, tabular
    return bundle


def main() -> None:
    seed_everything(42)
    bundle = load_bundle()

    print("=== Baseline (tabular ML) models ===")
    run_baselines()

    print("=== Transformer ===")
    run_transformer(bundle)

    print("=== Hybrid fusion variants (A: concat, B: weighted, C: learned) ===")
    run_hybrid_variant(bundle, "concat")
    run_hybrid_variant(bundle, "weighted")
    run_hybrid_variant(bundle, "learned")

    print("=== Ablations (Hybrid - <component>) ===")
    att_seq = FEATURE_GROUPS["attendance"]
    att_tab = [f for f in att_seq if True]
    run_hybrid_variant(
        zeroed_bundle(bundle, att_seq, att_tab), "learned", name_suffix="no-attendance",
        exclude_seq=att_seq, exclude_tab=att_tab, notes="Hybrid without attendance features",
    )
    beh_seq = FEATURE_GROUPS["behaviour"]
    run_hybrid_variant(
        zeroed_bundle(bundle, beh_seq, beh_seq), "learned", name_suffix="no-behaviour",
        exclude_seq=beh_seq, exclude_tab=beh_seq, notes="Hybrid without behavioural features",
    )
    hist_tab = ["previous_gpa"]
    run_hybrid_variant(
        zeroed_bundle(bundle, [], hist_tab), "learned", name_suffix="no-historical",
        exclude_seq=[], exclude_tab=hist_tab, notes="Hybrid without historical performance (previous GPA)",
    )

    # ---------------------------------------------------------------- persistence
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": "v1",
        "risk_threshold": RISK_SCORE_THRESHOLD,
        "experiments": EXPERIMENTS,
    }
    from ml.config import DATA_PROCESSED_DIR

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = DATA_PROCESSED_DIR / "experiment_report.csv"
    rows = []
    for e in EXPERIMENTS:
        m = e["metrics"]
        # baselines store flat metric dicts; torch models nest under regression/classification
        val_r = m["validation"].get("regression") or (m["validation"] if "MAE" in m["validation"] else {})
        test_r = m["test"].get("regression") or (m["test"] if "MAE" in m["test"] else {})
        val_c = m["validation"].get("classification") or (m["validation"] if "F1" in m["validation"] else {})
        test_c = m["test"].get("classification") or (m["test"] if "F1" in m["test"] else {})
        rows.append(
            {
                "experiment": e["experiment_name"],
                "model_type": e["model_type"],
                "val_RMSE": val_r.get("RMSE"),
                "val_R2": val_r.get("R2"),
                "val_F1": val_c.get("F1"),
                "test_RMSE": test_r.get("RMSE"),
                "test_R2": test_r.get("R2"),
                "test_MAE": test_r.get("MAE"),
                "test_Accuracy": test_c.get("Accuracy"),
                "test_F1": test_c.get("F1"),
                "test_ROC_AUC": test_c.get("ROC_AUC"),
                "duration_s": e["training_duration_seconds"],
                "notes": e["notes"],
            }
        )
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    (DATA_PROCESSED_DIR / "experiment_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nExperiment report saved: {out_csv} ({len(EXPERIMENTS)} experiments)")


if __name__ == "__main__":
    main()
