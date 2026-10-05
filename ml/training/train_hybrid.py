"""Hybrid model training CLI (§14): ML representation + Transformer representation.

Run from the project root:
    python -m ml.training.train_hybrid --fusion learned
"""
import argparse
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import torch

from ml.config import (
    HYBRID_FILE,
    HYBRID_METADATA_FILE,
    HYBRID_PREPROCESSOR_FILE,
    MODEL_VERSION,
    RISK_SCORE_THRESHOLD,
    SEQUENCE_STATS_FILE,
    TransformerConfig,
)
from ml.models.hybrid import HybridModel
from ml.training.torch_common import load_bundle, train_model


def run(config: TransformerConfig, epochs: int, batch_size: int, lr: float, patience: int, ablation_groups: list[str] | None = None) -> dict:
    bundle = load_bundle()
    n_tabular = len(bundle.feature_columns)
    model = HybridModel(n_tabular_features=n_tabular, config=config)
    print(f"Hybrid ({config.fusion} fusion): {sum(p.numel() for p in model.parameters()):,} parameters | device={bundle.device}")

    result = train_model(
        model, bundle, model_kind="hybrid",
        epochs=epochs, batch_size=batch_size, learning_rate=lr, patience=patience,
        checkpoint_path=HYBRID_FILE, log_prefix=f"[hybrid:{config.fusion}] ",
    )

    from sklearn.preprocessing import StandardScaler  # noqa: F401  (scaler loaded by name)

    HYBRID_FILE.parent.mkdir(parents=True, exist_ok=True)
    preprocessor_payload = {
        "tabular_scaler": bundle._tab_scaler,
        "sequence_stats": json.loads(SEQUENCE_STATS_FILE.read_text(encoding="utf-8")),
        "target_mean": bundle.target_mean,
        "target_std": bundle.target_std,
        "ablation_groups": ablation_groups or [],
    }
    preprocessor_file = (
        HYBRID_PREPROCESSOR_FILE
        if not ablation_groups
        else HYBRID_PREPROCESSOR_FILE.with_name(f"hybrid_preprocessor_{'_'.join(ablation_groups)}.joblib")
    )
    joblib.dump(preprocessor_payload, preprocessor_file)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_name": "HybridMLTransformer",
        "model_version": MODEL_VERSION,
        "model_type": "HYBRID",
        "architecture": config.to_dict(),
        "hyperparameters": {"epochs": epochs, "batch_size": batch_size, "learning_rate": lr, "patience": patience},
        "device": str(bundle.device),
        "risk_threshold": RISK_SCORE_THRESHOLD,
        "target_mean": bundle.target_mean,
        "target_std": bundle.target_std,
        "feature_columns": bundle.feature_columns,
        "ablation_groups": ablation_groups or [],
        "validation_metrics": result["validation"],
        "test_metrics": result["test"],
        "best_epoch": result["best_epoch"],
        "training_duration_seconds": result["training_duration_seconds"],
    }
    out_file = (
        HYBRID_METADATA_FILE
        if not ablation_groups
        else HYBRID_METADATA_FILE.with_name(f"hybrid_metadata_{'_'.join(ablation_groups) or 'full'}.json")
    )
    out_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"\n[hybrid] validation: {result['validation']['regression']} | {result['validation']['classification']}")
    print(f"[hybrid] test:       {result['test']['regression']} | {result['test']['classification']}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Hybrid ML + Transformer model")
    parser.add_argument("--fusion", choices=["concat", "weighted", "learned"], default="learned")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=20)
    args = parser.parse_args()

    config = TransformerConfig(fusion=args.fusion)
    run(config, args.epochs, args.batch_size, args.learning_rate, args.patience)


if __name__ == "__main__":
    main()
