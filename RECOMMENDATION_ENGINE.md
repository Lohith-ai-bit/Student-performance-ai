# Recommendation Engine

`backend/app/services/recommendation_service.py` — rule-based, student-specific, explanation-aware.

## Pipeline (§23-§27)

```text
Prediction + risk
      ↓
Weak-area detection (§24)
  ├─ weak course         (lowest in-progress average < 65)
  ├─ weak assessment type (weakest type within that course)
  ├─ attendance weakness (< 80%)
  └─ behaviour weakness  (low video completion / practice / late submissions)
      ↓            ↑ severity modifiers from SHAP/GRADIENT factors
Resource matching (§27) — learning_resources filtered by course + suggested type
      ↓
Candidate generation (§25) — rule templates per weak area
      ↓
Ranking (§26) — configurable weights (app/core/recommendation_config.py):
      score = w_risk·risk + w_severity·severity + w_recent_decline·decline
            + w_resource_relevance·match + w_difficulty_fit·fit + w_feedback·history
      ↓
Persist top-N (default 6; 2 for genuinely low-risk students)
```

## Feedback + progress (§28/§52)

Students can `Start` / `Mark complete` / `Dismiss` (`PATCH /recommendations/{id}`) and rate +
helpful/not-helpful (`POST /recommendations/{id}/feedback`). Feedback is stored in
`recommendation_feedback` and included as a ranking factor. `GET /students/me/learning-progress`
reports learning hours, practice questions and completion counts.

## Evaluation honesty (§52)

The system tracks generated/started/completed counts and ratings, and before/after performance is
available from the prediction history. **No causal improvement claim is made** — that requires a
controlled experiment (e.g. randomized recommendation exposure), which is future work.

## Rules of engagement (§49)

Recommendations are decision support. The system never automatically fails, suspends, penalizes
or restricts a student based on predictions; faculty interventions are recorded as human decisions.
