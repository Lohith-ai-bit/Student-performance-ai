# Explainability (SHAP + LIME)

Every stored prediction can be explained. Factors are persisted in `prediction_explanations`
(method, feature, importance, direction, human-readable text) and served by
`GET /api/v1/predictions/{predictionId}/explanation`.

```json
{
  "prediction": { "predicted_score": 74.9, "risk_level": "LOW", "model_type": "BASELINE", "...": "..." },
  "shap":   [ { "feature": "quiz_average", "importance": 0.14, "direction": "positive", "..." : "..." } ],
  "lime":   [ { "feature": "attendance_percentage", "importance": -0.06, "direction": "negative", "..." : "..." } ],
  "gradient": [],
  "summary": "The model estimates a predicted final score of about 75% with a low risk level. ...",
  "factors": [ ... ],
  "disclaimer": "This prediction is an AI-generated estimate intended to support learning and academic intervention. It should not be treated as a definitive judgment of student ability."
}
```

## Which method runs where

| Model | Methods |
|---|---|
| Baseline (tabular sklearn pipeline) | **SHAP** (KernelExplainer over the numeric features, categoricals held constant) + **LIME** (local linear surrogate) |
| Transformer / Hybrid | **Gradient × input** attribution over the attended time steps (labeled `GRADIENT` — stored honestly, not as SHAP) |

## Human-readable layer (§21)

`ml/explainability/labels.py` maps technical feature names to friendly labels
("quiz_average" → "Quiz performance") and produces supportive sentences. The summary is
templated from the top factors. Language rules:

- ✅ "The model estimates an increased risk of low performance."
- ✅ "Working in the student's favour: quiz performance, attendance."
- ❌ Never "You will fail." — never a verdict, never a decision.

## Where explanations appear

- Student dashboard: **Why this prediction?** card (`PredictionCard` + `FactorList`)
- Student prediction page: full summary + factors
- Faculty student detail: AI explanation card for the latest prediction
