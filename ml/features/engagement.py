"""Engineered engagement score.

Initial rule-based feature with configurable weights (§22). The weights are a
design choice, NOT scientifically validated — Phase 2/3 will replace this score
with learned representations from the Transformer.

This module is the single source of truth; the backend re-exports from here.
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

ENGAGEMENT_NORM_CAPS = {
    "logins_per_week_cap": 7.0,
    "session_hours_per_week_cap": 10.0,
    "practice_per_week_cap": 50.0,
}

# Quiz attempts per week considered fully engaged
QUIZ_ATTEMPTS_PER_WEEK_CAP = 4.0


def compute_engagement_score(
    video_completion_rate: float | None,
    assignment_submission_rate: float | None,
    logins_per_week: float | None,
    session_hours_per_week: float | None,
    quiz_attempts_per_week: float | None,
    practice_questions_per_week: float | None,
    late_submission_rate: float | None,
) -> float:
    """Weighted average of normalized sub-signals in [0, 1]. Missing signals are neutral (0.5)."""
    caps = ENGAGEMENT_NORM_CAPS
    w = ENGAGEMENT_WEIGHTS

    def norm(value: float | None, cap: float) -> float:
        if value is None:
            return 0.5
        return max(0.0, min(1.0, float(value) / cap)) if cap > 0 else 0.0

    video = 0.5 if video_completion_rate is None else max(0.0, min(1.0, video_completion_rate))
    assign = 0.5 if assignment_submission_rate is None else max(0.0, min(1.0, assignment_submission_rate))

    late = 0.0 if late_submission_rate is None else max(0.0, min(1.0, late_submission_rate))

    parts = {
        "video_completion_rate": video * w["video_completion_rate"],
        "assignment_submission_rate": assign * w["assignment_submission_rate"],
        "login_frequency": norm(logins_per_week, caps["logins_per_week_cap"]) * w["login_frequency"],
        "session_duration_norm": norm(session_hours_per_week, caps["session_hours_per_week_cap"]) * w["session_duration_norm"],
        "quiz_attempt_rate": norm(quiz_attempts_per_week, QUIZ_ATTEMPTS_PER_WEEK_CAP) * w["quiz_attempt_rate"],
        "practice_question_count_norm": norm(
            practice_questions_per_week, caps["practice_per_week_cap"]
        ) * w["practice_question_count_norm"],
        "late_submission_penalty": (1.0 - late) * w["late_submission_penalty"],
    }
    return round(sum(parts.values()), 4)
