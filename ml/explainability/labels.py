"""Human-readable feature labels used by all explanation surfaces (§19/§21)."""

FEATURE_LABELS = {
    "quiz_average": "Quiz performance",
    "assignment_average": "Assignment performance",
    "midterm_score": "Midterm score",
    "lab_average": "Lab performance",
    "project_average": "Project performance",
    "assessment_count": "Assessment coverage",
    "score_trend": "Recent score trend",
    "attendance_percentage": "Attendance",
    "attendance_trend": "Attendance trend",
    "logins_per_week": "Login frequency",
    "session_hours_per_week": "Weekly study time",
    "documents_per_week": "Document study",
    "quiz_attempts_per_week": "Quiz attempts",
    "practice_questions_per_week": "Practice questions",
    "videos_watched_per_week": "Videos watched",
    "video_completion_rate": "Video completion rate",
    "assignments_submitted_per_week": "Assignment submissions",
    "assignment_submission_rate": "Assignment completion rate",
    "late_submission_rate": "Late submissions",
    "engagement_score": "Engagement",
    "previous_gpa": "Previous GPA",
    "course_semester": "Course level",
    "admission_year": "Admission year",
    "department": "Department",
    "branch": "Branch",
}

# sequence feature labels (Transformer side)
SEQUENCE_FEATURE_LABELS = {
    "attendance_percentage": "Weekly attendance",
    "quiz_average": "Weekly quiz performance",
    "assignment_average": "Weekly assignment performance",
    "midterm_score": "Midterm performance",
    "session_duration": "Weekly study hours",
    "video_completion_rate": "Video completion",
    "quiz_attempts": "Weekly quiz attempts",
    "assignment_submission_rate": "Weekly submission rate",
    "practice_questions": "Practice questions",
    "login_frequency": "Weekly logins",
    "engagement_score": "Engagement",
    "performance_trend": "Performance trend",
    "attendance_trend": "Attendance trend",
}


def label_for(feature: str) -> str:
    return FEATURE_LABELS.get(feature) or SEQUENCE_FEATURE_LABELS.get(feature) or feature.replace("_", " ").title()


def describe_factor(label: str, importance: float, direction: str) -> str:
    """Turn a raw factor into an understandable, non-judgmental sentence (§21)."""
    if direction == "positive":
        return f"{label} is contributing positively to the predicted outcome."
    return f"{label} is pulling the prediction downward and may need attention."
