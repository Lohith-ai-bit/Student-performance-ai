# Transformer

A **structured-temporal Transformer** (not an NLP model): the input is a student's weekly
learning-behaviour matrix, not text.

```
Input sequence [B, T, F]        T = 12 weeks, F = 13 features
      ↓
Feature projection   Linear(F → d_model)
      ↓
Positional encoding  sinusoidal (padded steps neutralized by the attention mask)
      ↓
Transformer encoder  nn.TransformerEncoder, batch_first, GELU, dropout
      ↓
Attention pooling    masked softmax over time → one student representation [B, d_model]
      ↓
Prediction heads     regression (score) + classification (risk logit)
```

## Configuration

All hyperparameters live in `ml/config.py::TransformerConfig`
(`sequence_length, n_features, embedding_dimension, attention_heads, encoder_layers,
feedforward_dimension, dropout`) — never scattered through the code. Architecture values are
saved into the model metadata and restored at inference.

## Training (`ml/training/train_transformer.py`)

- Sequence export → 70/15/15 split (indices match the Phase 1 split by seed)
- Multi-task loss: MSE (standardized score) + BCE (risk)
- Early stopping on validation RMSE; best checkpoint saved to `model_transformer.pt`
- Reproducible seeds; CPU/GPU with mixed precision when CUDA is available

```bash
python -m ml.sequences.export_sequences
python -m ml.training.train_transformer --epochs 150 --batch-size 32
```

## Actual results (synthetic dataset, 480 sequences; do not generalize)

| Split | Regression | Classification |
|---|---|---|
| Validation | MAE 11.3 · RMSE 14.4 · R² 0.678 | Acc 0.861 · F1 0.737 · ROC-AUC 0.935 |
| Test | MAE 12.9 · RMSE 15.5 · R² 0.562 | Acc 0.847 · F1 0.766 · ROC-AUC 0.909 |

On this small synthetic dataset the transformer-only model is *weaker* than the tabular
baselines — there is limited temporal signal in 12 weeks of sparse weekly aggregates. The honest
conclusion is recorded in the experiment dashboard; the Hybrid model (see
[HYBRID_MODEL.md](HYBRID_MODEL.md)) exists to combine both views.
