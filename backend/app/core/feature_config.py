"""Engineered engagement score configuration.

The engagement score is an initial, rule-based engineered feature. Its weights
are deliberately configurable (NOT presented as scientifically validated) —
Phase 2/3 will replace it with learned representations from the Transformer.

Weights should sum to 1.0; the score is a weighted average of normalized
sub-signals in [0, 1].
"""
ENGAGEMENT_WEIGHTS = {
    "video_completion_rate": 0.20,
    "assignment_submission_rate": 0.20,
    "login_frequency": 0.15,
    "session_duration_norm": 0.15,
    "quiz_attempt_rate": 0.15,
    "practice_question_count_norm": 0.10,
    "late_submission_penalty": 0.05,
}

# Normalization caps for rate features (values are capped at 1.0 after division).
ENGAGEMENT_NORM_CAPS = {
    # logins per week considered "fully active"
    "logins_per_week_cap": 7.0,
    # hours of learning sessions per week considered "fully engaged"
    "session_hours_per_week_cap": 10.0,
    # practice questions per week considered fully engaged
    "practice_per_week_cap": 50.0,
}
