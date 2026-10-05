# ML Architecture

```text
                STUDENT DATA
                     |
     ┌───────────────┼────────────────┐
     ↓               ↓                ↓
 Academic         Attendance      Behaviour
     |               |                |
     └───────────────┼────────────────┘
                     ↓
              Feature Engineering
                     |
        ┌────────────┴────────────┐
        ↓                         ↓
   Tabular Data              Temporal Data
   (ml/features)             (ml/sequences)
        ↓                         ↓
   ML Encoder               Transformer
   (Phase 1 pipelines)      (ml/models/transformer.py)
        ↓                         ↓
 ML Representation     Transformer Representation
        └────────────┬────────────┘
                     ↓
              Fusion Layer (concat | weighted | learned)
                     ↓
              Hybrid Predictor (ml/models/hybrid.py)
                     ↓
       ┌─────────────┴─────────────┐
       ↓                           ↓
Performance Prediction       Risk Prediction
       |                           |
       └─────────────┬─────────────┘
                     ↓
               Explainability (SHAP / LIME / gradient)
                     ↓
          Recommendation Engine
                     ↓
          Personalized Learning + Feedback
                     ↓
             Model Monitoring / Drift
```

## Tabular features (Phase 1, reused)

One row per (student, course): quiz/assignment/midterm/lab/project averages, score trend,
attendance percentage + trend, per-week behavioural rates, configurable engagement score,
demographics, previous GPA. Target: ENDTERM percentage (regression) and at-risk flag
(score < 50 by default) for classification.

## Temporal sequences (Phase 2)

One sequence per (student, course): up to 12 weekly vectors of 13 features
(attendance, quiz/assignment/midterm, study hours, video completion, attempts, submission rate,
practice, logins, engagement, performance/attendance trends). Weeks are chronological
(oldest → newest); missing weeks are masked. Exported by `python -m ml.sequences.export_sequences`.

## Models

| Model | Input | Family | Artifact |
|---|---|---|---|
| Baseline | tabular | Linear/Logistic Regression, Random Forest, XGBoost, LightGBM | `ml/artifacts/model_{regression,classification}.joblib` |
| Transformer | sequence | PyTorch `nn.TransformerEncoder` + attention pooling + dual heads | `ml/artifacts/model_transformer.pt` |
| Hybrid | tabular + sequence | TabularEncoder ⊕ Transformer ⊕ fusion + dual heads | `ml/artifacts/model_hybrid.pt` |

All preprocessing (imputation, scaling, one-hot encoding) is fitted inside pipelines on the
training split only. See [TRANSFORMER.md](TRANSFORMER.md) and [HYBRID_MODEL.md](HYBRID_MODEL.md).
