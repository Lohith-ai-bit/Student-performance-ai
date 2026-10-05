"""Shared PyTorch training infrastructure for the Transformer and Hybrid models (§10/§14).

Handles: reproducible seeding, data loading from the exported .npz, target
scaling, the train/validate loop with early stopping, checkpointing, and final
evaluation. GPU + mixed precision are used when available.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from ml.evaluation.metrics import classification_metrics, regression_metrics
from ml.sequences.collator import SequenceCollator
from ml.sequences.dataset import SequenceDataset, standardize
from ml.sequences.dataset import load_sequences_bundle


def seed_everything(seed: int = 42) -> None:
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


@dataclass
class Bundle:
    sequences: np.ndarray
    masks: np.ndarray
    tabular: np.ndarray
    y_reg: np.ndarray
    y_cls: np.ndarray
    splits: dict
    feature_columns: list
    device: torch.device
    target_mean: float = 0.0
    target_std: float = 1.0

    def dataset(self, indices: np.ndarray) -> SequenceDataset:
        seqs = standardize(self.sequences[indices], self.masks[indices], {
            "mean": self._seq_mean, "std": self._seq_std,
        })
        tab = self._tab_scaler.transform(self.tabular[indices]).astype(np.float32)
        y_reg_std = (self.y_reg[indices] - self.target_mean) / self.target_std
        return SequenceDataset(seqs, self.masks[indices], tab, y_reg_std.astype(np.float32), self.y_cls[indices])

    # populated by load_bundle()
    _seq_mean: list = field(default_factory=list)
    _seq_std: list = field(default_factory=list)
    _tab_scaler: object = None


def load_bundle(bundle_files=None) -> Bundle:
    """Load sequences + tabular; fit preprocessing on the TRAIN split only (no leakage)."""
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    data, index, stats = load_sequences_bundle()
    train_idx = np.array(index["splits"]["train"])

    bundle = Bundle(
        sequences=data["sequences"],
        masks=data["masks"],
        tabular=data["tabular"],
        y_reg=data["y_regression"],
        y_cls=data["y_classification"],
        splits=index["splits"],
        feature_columns=index["feature_columns"],
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
    )
    bundle._seq_mean = stats["mean"]
    bundle._seq_std = stats["std"]
    bundle.target_mean = float(bundle.y_reg[train_idx].mean())
    bundle.target_std = float(bundle.y_reg[train_idx].std())
    # median imputation + standardization (NaNs exist for sparse features like lab_average);
    # keep_empty_features preserves all-NaN columns so dimensions stay fixed
    bundle._tab_scaler = Pipeline(
        [("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("scaler", StandardScaler())]
    ).fit(bundle.tabular[train_idx])
    return bundle


def make_loader(bundle: Bundle, indices: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    return DataLoader(
        bundle.dataset(indices),
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=SequenceCollator(max_length=bundle.sequences.shape[1]),
    )


def run_forward(model, batch: dict, model_kind: str) -> dict:
    if model_kind == "hybrid":
        return model(batch["sequence"], batch["mask"], batch["tabular"])
    return model(batch["sequence"], batch["mask"])


def train_model(
    model: torch.nn.Module,
    bundle: Bundle,
    model_kind: str,
    epochs: int = 120,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    patience: int = 15,
    checkpoint_path: Path | None = None,
    seed: int = 42,
    log_prefix: str = "",
) -> dict:
    """Train with early stopping on validation RMSE; returns best-val metrics + history."""
    seed_everything(seed)
    device = bundle.device
    model.to(device)

    train_loader = make_loader(bundle, np.array(bundle.splits["train"]), batch_size, shuffle=True)
    val_loader = make_loader(bundle, np.array(bundle.splits["validation"]), batch_size, shuffle=False)

    mse = torch.nn.MSELoss()
    bce = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)

    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_val_rmse = float("inf")
    best_state = None
    best_epoch = -1
    history = []
    start = time.time()

    for epoch in range(epochs):
        model.train()
        train_losses = []
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad()
            with torch.autocast(device_type=device.type, enabled=use_amp):
                out = run_forward(model, batch, model_kind)
                loss = mse(out["score"], batch["y_regression"]) + bce(out["risk_logit"], batch["y_classification"])
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_losses.append(loss.item())

        val = evaluate_model(model, bundle, model_kind, split="validation")
        scheduler.step(val["regression"]["RMSE"])
        history.append({"epoch": epoch, "train_loss": float(np.mean(train_losses)), **{k: v for k, v in val["regression"].items()}})

        if val["regression"]["RMSE"] < best_val_rmse:
            best_val_rmse = val["regression"]["RMSE"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch

        if epoch % 10 == 0 or epoch == epochs - 1:
            print(f"{log_prefix}[epoch {epoch:3d}] train_loss={np.mean(train_losses):.4f} val_RMSE={val['regression']['RMSE']:.4f} val_F1={val['classification']['F1']}")

        if epoch - best_epoch >= patience:
            print(f"{log_prefix}Early stopping at epoch {epoch} (best {best_epoch})")
            break

    duration = time.time() - start
    if best_state is not None and checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(best_state, checkpoint_path)
        model.load_state_dict(best_state)

    return {
        "training_duration_seconds": round(duration, 2),
        "best_epoch": best_epoch,
        "history": history,
        "validation": evaluate_model(model, bundle, model_kind, split="validation"),
        "test": evaluate_model(model, bundle, model_kind, split="test"),
    }


def evaluate_model(model: torch.nn.Module, bundle: Bundle, model_kind: str, split: str) -> dict:
    device = bundle.device
    loader = make_loader(bundle, np.array(bundle.splits[split]), batch_size=64, shuffle=False)
    model.eval()
    scores_std, risks, ys_reg, ys_cls = [], [], [], []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = run_forward(model, batch, model_kind)
            scores_std.append(out["score"].cpu().numpy())
            risks.append(torch.sigmoid(out["risk_logit"]).cpu().numpy())
            ys_reg.append(batch["y_regression"].cpu().numpy())
            ys_cls.append(batch["y_classification"].cpu().numpy())

    scores_std = np.concatenate(scores_std)
    scores = scores_std * bundle.target_std + bundle.target_mean  # inverse target scaling
    ys_reg = np.concatenate(ys_reg) * bundle.target_std + bundle.target_mean
    risks = np.concatenate(risks)
    ys_cls = np.concatenate(ys_cls)
    preds = (risks >= 0.5).astype(int)

    return {
        "regression": regression_metrics(ys_reg, scores),
        "classification": classification_metrics(ys_cls, preds, risks),
    }
