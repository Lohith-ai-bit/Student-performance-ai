# Hybrid Model

The primary research component (§12-14): combines the Phase 1 tabular representation with the
Transformer's temporal representation.

```
Tabular features [B, K]           Learning sequence [B, T, F]
      ↓                                  ↓
TabularEncoder (MLP)             TransformerPredictor.encode
      ↓                                  ↓
ML representation [B, D]   Transformer representation [B, D]
      └──────────────┬───────────────┘
                     ↓
              FusionLayer
                     ↓
         MLP head → score + risk logit
```

## Fusion methods (configurable — `TransformerConfig(fusion=...)`)

| Method | Formula |
|---|---|
| `concat` (A) | `[ML_repr ; Seq_repr]` |
| `weighted` (B) | `sigmoid(α)·ML_repr + sigmoid(β)·Seq_repr` (learnable α, β) |
| `learned` (C, default) | Data-dependent gate: `softmax(gate([ML;Seq]))` over both representations |

## Training (`ml/training/train_hybrid.py`)

```bash
python -m ml.training.train_hybrid --fusion learned
```

The tabular preprocessor (median imputer + standardizer, fitted on the train split) and the
sequence standardization statistics are saved alongside the checkpoint (`hybrid_preprocessor.joblib`,
`sequence_stats.json`) so live inference reproduces training-time preprocessing exactly.

## Ablations (§16/§53)

`python -m ml.training.compare_models` trains the full hybrid plus ablated variants
(zeroed feature groups: −attendance, −behaviour, −historical performance) and records every run
in `model_experiments`. See the experiment dashboard (`/admin/experiments`) for the actual numbers.

## Actual test results (synthetic dataset — same split for all models)

| Model | RMSE ↓ | R² | F1 | ROC-AUC |
|---|---|---|---|---|
| LinearRegression (baseline) | **9.41** | **0.839** | 0.818 | 0.960 |
| RandomForest (baseline) | 10.38 | 0.804 | 0.810 | 0.957 |
| Transformer only | 15.09 | 0.587 | 0.792 | 0.919 |
| **Hybrid (learned fusion)** | 9.86 | 0.824 | **0.844** | 0.953 |
| Hybrid − attendance | 10.42 | 0.803 | 0.791 | 0.950 |
| Hybrid − behaviour | 10.42 | 0.803 | 0.844 | 0.953 |
| Hybrid − historical | 10.76 | 0.790 | 0.762 | 0.941 |

**Honest reading:** on this small synthetic dataset the hybrid clearly beats the transformer-only
model and the tree ensembles, is the best classifier (F1), but narrowly trails plain
LinearRegression on regression RMSE. Ablations show every component contributes. No claim of
Hybrid > ML is made beyond what these runs show.
