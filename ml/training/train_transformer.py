"""Transformer training CLI (§10).

Run from the project root (after `python -m ml.sequences.export_sequences`):
    python -m ml.training.train_transformer
"""
import argparse
import json
from datetime import datetime, timezone

import torch

from ml.config import (
    MODEL_VERSION,
    RISK_SCORE_THRESHOLD,
    TRANSFORMER_FILE,
    TRANSFORMER_METADATA_FILE,
    TransformerConfig,
)
from ml.models.transformer import TransformerPredictor
from ml.training.torch_common import load_bundle, train_model


def run(config: TransformerConfig, epochs: int, batch_size: int, lr: float, patience: int) -> dict:
    bundle = load_bundle()
    model = TransformerPredictor(config)
    print(f"Transformer: {sum(p.numel() for p in model.parameters()):,} parameters | device={bundle.device}")

    result = train_model(
        model, bundle, model_kind="transformer",
        epochs=epochs, batch_size=batch_size, learning_rate=lr, patience=patience,
        checkpoint_path=TRANSFORMER_FILE, log_prefix="[transformer] ",
    )

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_name": "TemporalTransformer",
        "model_version": MODEL_VERSION,
        "model_type": "TRANSFORMER",
        "architecture": config.to_dict(),
        "hyperparameters": {"epochs": epochs, "batch_size": batch_size, "learning_rate": lr, "patience": patience},
        "device": str(bundle.device),
        "risk_threshold": RISK_SCORE_THRESHOLD,
        "target_mean": bundle.target_mean,
        "target_std": bundle.target_std,
        "feature_columns": bundle.feature_columns,
        "validation_metrics": result["validation"],
        "test_metrics": result["test"],
        "best_epoch": result["best_epoch"],
        "training_duration_seconds": result["training_duration_seconds"],
        "history": result["history"],
    }
    TRANSFORMER_METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"\n[transformer] validation: {result['validation']['regression']} | {result['validation']['classification']}")
    print(f"[transformer] test:       {result['test']['regression']} | {result['test']['classification']}")
    print(f"Saved checkpoint to {TRANSFORMER_FILE} and metadata to {TRANSFORMER_METADATA_FILE}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the temporal Transformer")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--embedding-dimension", type=int, default=64)
    parser.add_argument("--encoder-layers", type=int, default=2)
    parser.add_argument("--attention-heads", type=int, default=4)
    args = parser.parse_args()

    config = TransformerConfig(
        embedding_dimension=args.embedding_dimension,
        encoder_layers=args.encoder_layers,
        attention_heads=args.attention_heads,
    )
    run(config, args.epochs, args.batch_size, args.learning_rate, args.patience)


if __name__ == "__main__":
    main()
