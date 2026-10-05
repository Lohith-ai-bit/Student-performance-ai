"""Hybrid model (§12/§13): tabular ML representation + Transformer temporal
representation -> fusion -> MLP head.

Fusion methods (configurable):
  concat    — concatenate both representations
  weighted  — learnable scalar gate: alpha * ML + beta * Transformer
  learned   — MLP attention over the two representations (default)
"""
import torch
import torch.nn as nn

from ml.config import TransformerConfig
from ml.models.transformer import TransformerPredictor


class TabularEncoder(nn.Module):
    """ML-side encoder: MLP over the (standardized) tabular feature vector."""

    def __init__(self, n_tabular_features: int, hidden: int = 64, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_tabular_features, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )
        self.out_dim = hidden

    def forward(self, tabular: torch.Tensor) -> torch.Tensor:
        return self.net(tabular)


class FusionLayer(nn.Module):
    def __init__(self, method: str, representation_dim: int):
        super().__init__()
        self.method = method
        if method == "concat":
            self.out_dim = representation_dim * 2
        elif method == "weighted":
            self.alpha = nn.Parameter(torch.tensor(0.5))
            self.beta = nn.Parameter(torch.tensor(0.5))
            self.out_dim = representation_dim
        elif method == "learned":
            self.gate = nn.Sequential(
                nn.Linear(representation_dim * 2, representation_dim),
                nn.Tanh(),
                nn.Linear(representation_dim, 2),
            )
            self.project = nn.Linear(representation_dim * 2, representation_dim)
            self.out_dim = representation_dim
        else:
            raise ValueError(f"Unknown fusion method: {method}")

    def forward(self, ml_repr: torch.Tensor, seq_repr: torch.Tensor) -> torch.Tensor:
        if self.method == "concat":
            return torch.cat([ml_repr, seq_repr], dim=-1)
        if self.method == "weighted":
            a = torch.sigmoid(self.alpha)
            b = torch.sigmoid(self.beta)
            return a * ml_repr + b * seq_repr
        # learned: data-dependent gate over the two representations
        gate = torch.softmax(self.gate(torch.cat([ml_repr, seq_repr], dim=-1)), dim=-1)
        combined = self.project(torch.cat([ml_repr, seq_repr], dim=-1))
        return gate[:, 0:1] * ml_repr + gate[:, 1:2] * seq_repr


class HybridModel(nn.Module):
    """Full hybrid: Transformer encoder (sequence) + TabularEncoder (features) + fusion + heads."""

    def __init__(self, n_tabular_features: int, config: TransformerConfig | None = None):
        super().__init__()
        self.config = config or TransformerConfig()
        c = self.config

        self.transformer = TransformerPredictor(c)
        seq_dim = c.embedding_dimension  # transformer encode() output dim
        self.tabular_encoder = TabularEncoder(n_tabular_features, hidden=seq_dim, dropout=c.dropout)
        self.fusion = FusionLayer(c.fusion, representation_dim=seq_dim)

        fused = self.fusion.out_dim
        self.head = nn.Sequential(
            nn.Linear(fused, c.feedforward_dimension),
            nn.GELU(),
            nn.Dropout(c.dropout),
        )
        self.regression_head = nn.Linear(c.feedforward_dimension, 1)
        self.classification_head = nn.Linear(c.feedforward_dimension, 1)

    def forward(self, sequence: torch.Tensor, mask: torch.Tensor, tabular: torch.Tensor) -> dict:
        seq_repr = self.transformer.encode(sequence, mask)          # temporal representation
        ml_repr = self.tabular_encoder(tabular)                     # ML representation
        fused = self.fusion(ml_repr, seq_repr)
        hidden = self.head(fused)
        return {
            "representation": hidden,
            "ml_representation": ml_repr,
            "seq_representation": seq_repr,
            "score": self.regression_head(hidden).squeeze(-1),
            "risk_logit": self.classification_head(hidden).squeeze(-1),
        }
