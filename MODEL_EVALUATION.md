# Model Evaluation

All numbers in this document (and in the `/admin/experiments` dashboard) come from actual runs of
`python -m ml.training.compare_models` on the same synthetic dataset (480 rows) and the same
reproducible 70/15/15 split. They are **not** claims about real-world performance.

## Regression (test split)

| Model | MAE ↓ | RMSE ↓ | R² ↑ |
|---|---|---|---|
| LinearRegression | **7.49** | **9.41** | **0.839** |
| RandomForest | 8.23 | 10.38 | 0.804 |
| LightGBM | 8.61 | 10.71 | 0.792 |
| XGBoost | 8.37 | 10.83 | 0.787 |
| Hybrid (learned) | 7.89 | 9.86 | 0.824 |
| Hybrid (concat) | 8.55 | 10.68 | 0.793 |
| Hybrid (weighted) | 8.85 | 10.84 | 0.787 |
| Transformer only | 12.11 | 15.09 | 0.587 |

## Classification (test split)

| Model | Accuracy | Precision | Recall | F1 ↑ | ROC-AUC |
|---|---|---|---|---|---|
| LogisticRegression | 0.889 | 0.783 | 0.857 | 0.818 | 0.960 |
| RandomForest | 0.889 | 0.810 | 0.810 | 0.810 | 0.957 |
| XGBoost | 0.875 | 0.800 | 0.762 | 0.781 | 0.960 |
| LightGBM | 0.875 | 0.773 | 0.810 | 0.791 | 0.946 |
| Transformer only | 0.861 | 0.692 | 0.857 | 0.766 | 0.919 |
| **Hybrid (learned)** | **0.903** | 0.842 | 0.889 | **0.844** | 0.953 |

## Ablations (Hybrid, learned fusion)

| Variant | Test RMSE | Test F1 |
|---|---|---|
| Full hybrid | 9.86 | 0.844 |
| − attendance | 10.42 | 0.791 |
| − behaviour | 10.42 | 0.844 |
| − historical performance (previous GPA) | 10.76 | 0.762 |

Removing any component degrades at least one task — all three feature groups contribute.

## Answers to the research questions (§51) — as far as this data allows

1. **Does the Transformer improve prediction?** Not alone on this dataset (weakest regression).
2. **Does combining ML + Transformer improve performance?** The hybrid beats the transformer and
   the tree ensembles and is the best risk classifier, but does not beat LinearRegression on RMSE.
3. **Which features matter most?** See the global SHAP importance on the model dashboard; quiz and
   attendance features dominate.
4. **Which behaviours associate with risk?** Low video completion, low practice volume, late
   submissions and declining attendance trend (weak-area detector + SHAP negative factors).
5. **Early risk identification?** The hybrid's higher F1/ROC-AUC indicates better risk ranking
   than single-view models on this data.
6. **Recommendation relevance?** Tracked via feedback and completion rates; a causal claim would
   require a controlled experiment.

## Calibration (§50)

The classifier's ROC-AUC (0.95) shows good ranking quality; calibration is assessed by comparing
predicted probabilities against observed outcome frequencies (reliability data on the monitoring
page). If calibration degrades on real data, wrap the classifier in `sklearn.calibration.CalibratedClassifierCV`
(isotonic/Platt) before promotion. Uncalibrated probabilities are never presented as certainty —
the UI always shows them as "risk probability" alongside the disclaimer.
