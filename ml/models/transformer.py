"""Temporal Transformer over structured weekly learning data (§9).

Input Sequence -> Feature Projection -> Positional Encoding -> Transformer
Encoder -> (masked) Attention Pooling -> Student Representation -> Prediction Head.

Not an NLP transformer: inputs are per-week vectors of academic/attendance/
behaviour features for one (student, course).
"""
import math

import torch
import torch.nn as nn

from ml.config import TransformerConfig


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding; supports left-padded sequences via the mask."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(1, max_len, d_model)
        pe[0, :, 0::2] = torch.sin(position * div_term)
        pe[0, :, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Left-padded real tokens keep their relative order, which is what the
        # temporal encoder needs; padded steps are neutralized by the attention mask.
        seq_len = x.shape[1]
        return self.dropout(x + self.pe[:, :seq_len])


class AttentionPooling(nn.Module):
    """Masked softmax attention pooling over time -> single student representation."""

    def __init__(self, d_model: int):
        super().__init__()
        self.score = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        # x: [B, T, D], mask: [B, T] with 1 = real step
        scores = self.score(x).squeeze(-1)                      # [B, T]
        scores = scores.masked_fill(mask < 0.5, -1e9)
        weights = torch.softmax(scores, dim=-1)                 # [B, T]
        return torch.bmm(weights.unsqueeze(1), x).squeeze(1)    # [B, D]


class TransformerPredictor(nn.Module):
    """Sequence-only predictor: regression head (score) + classification head (risk logit)."""

    def __init__(self, config: TransformerConfig | None = None):
        super().__init__()
        self.config = config or TransformerConfig()
        c = self.config

        self.input_projection = nn.Linear(c.n_features, c.embedding_dimension)
        self.positional_encoding = PositionalEncoding(c.embedding_dimension, max_len=c.sequence_length * 2, dropout=c.dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=c.embedding_dimension,
            nhead=c.attention_heads,
            dim_feedforward=c.feedforward_dimension,
            dropout=c.dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=c.encoder_layers)
        self.pooling = AttentionPooling(c.embedding_dimension)
        self.head_hidden = nn.Sequential(
            nn.Linear(c.embedding_dimension, c.feedforward_dimension),
            nn.GELU(),
            nn.Dropout(c.dropout),
        )
        self.regression_head = nn.Linear(c.feedforward_dimension, 1)
        self.classification_head = nn.Linear(c.feedforward_dimension, 1)

    def encode(self, sequence: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        x = self.input_projection(sequence)
        x = self.positional_encoding(x)
        x = self.encoder(x, src_key_padding_mask=(mask < 0.5))
        return self.pooling(x, mask)  # student representation [B, D]

    def forward(self, sequence: torch.Tensor, mask: torch.Tensor):
        rep = self.encode(sequence, mask)
        hidden = self.head_hidden(rep)
        return {
            "representation": rep,
            "score": self.regression_head(hidden).squeeze(-1),
            "risk_logit": self.classification_head(hidden).squeeze(-1),
        }

    def predict(
        self, sequence: torch.Tensor, mask: torch.Tensor, risk_score_threshold: float = 50.0
    ) -> dict:
        """Inference-friendly output in original units (standardization is inverted upstream)."""
        self.eval()
        with torch.no_grad():
            out = self.forward(sequence, mask)
        # score head was trained on standardized targets -> denormalized by the caller;
        # here we return raw head outputs plus risk probability
        return {
            "representation": out["representation"],
            "score": out["score"],
            "risk_probability": torch.sigmoid(out["risk_logit"]),
        }
