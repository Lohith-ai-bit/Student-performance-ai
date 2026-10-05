"""PyTorch Dataset for temporal student sequences (§7/§10)."""
import json

import numpy as np
import torch
from torch.utils.data import Dataset

from ml.config import SEQUENCE_FEATURES


class SequenceDataset(Dataset):
    """Yields (sequence, mask, tabular, y_reg, y_cls) tensors.

    `tabular` carries the Phase 1 tabular feature vector (standardized) so the
    Hybrid model can consume the same dataset; the pure Transformer ignores it.
    """

    def __init__(
        self,
        sequences: np.ndarray,     # [N, T, F] float32, padded/standardized
        masks: np.ndarray,         # [N, T] float32
        tabular: np.ndarray,       # [N, K] float32 (standardized)
        y_regression: np.ndarray,  # [N] float32
        y_classification: np.ndarray,  # [N] float32 (0/1)
    ):
        self.sequences = torch.from_numpy(sequences.astype(np.float32))
        self.masks = torch.from_numpy(masks.astype(np.float32))
        self.tabular = torch.from_numpy(tabular.astype(np.float32))
        self.y_regression = torch.from_numpy(y_regression.astype(np.float32))
        self.y_classification = torch.from_numpy(y_classification.astype(np.float32))

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int):
        return {
            "sequence": self.sequences[idx],
            "mask": self.masks[idx],
            "tabular": self.tabular[idx],
            "y_regression": self.y_regression[idx],
            "y_classification": self.y_classification[idx],
        }


def load_sequences_bundle(data_dir=None):
    """Load the exported .npz + stats + index produced by ml.sequences.export_sequences."""
    from ml.config import SEQUENCES_FILE, SEQUENCES_INDEX_FILE, SEQUENCE_STATS_FILE

    data = np.load(SEQUENCES_FILE)
    index = json.loads(SEQUENCES_INDEX_FILE.read_text(encoding="utf-8"))
    stats = json.loads(SEQUENCE_STATS_FILE.read_text(encoding="utf-8"))
    return data, index, stats


def standardize(sequences: np.ndarray, masks: np.ndarray, stats: dict) -> np.ndarray:
    """Apply per-feature standardization using training-split statistics.

    Missing (masked) steps become 0 (= mean) so they do not distort attention.
    """
    mu = np.array(stats["mean"], dtype=np.float32)
    sd = np.array(stats["std"], dtype=np.float32)
    sd[sd < 1e-8] = 1.0
    out = (sequences - mu) / sd
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    out = out * masks[..., None]
    return out.astype(np.float32)


def compute_stats(sequences: np.ndarray, masks: np.ndarray) -> dict:
    """Per-feature mean/std over VALID (mask=1) steps only — computed on the training split."""
    valid = masks.astype(bool)
    flat = sequences[valid]  # [n_valid_steps, F]
    mean = flat.mean(axis=0)
    std = flat.std(axis=0)
    std[std < 1e-8] = 1.0
    return {"mean": mean.tolist(), "std": std.tolist()}
