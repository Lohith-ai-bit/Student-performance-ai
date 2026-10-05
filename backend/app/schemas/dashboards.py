"""Aggregated dashboard payloads for student / faculty / admin views."""
from pydantic import BaseModel


class StudentSummary(BaseModel):
    gpa: float | None = None
    predicted_score: float | None = None
    attendance_percentage: float | None = None
    engagement_score: float | None = None
    risk_level: str | None = None


class StudentDashboardResponse(BaseModel):
    success: bool = True
    student: dict
    summary: StudentSummary
    performance: list[dict] = []   # [{course, average_percentage, ...}]
    performance_trend: list[dict] = []  # [{label, previous, current, predicted}]
    attendance: list[dict] = []    # [{course, percentage, conducted, attended}]
    latest_prediction: dict | None = None


class FacultyDashboardResponse(BaseModel):
    success: bool = True
    totals: dict  # {students, avg_performance, avg_attendance, high_risk, medium_risk, low_risk}
    performance_distribution: list[dict] = []  # [{bucket, count}]
    risk_distribution: list[dict] = []          # [{level, count}]
    attendance_distribution: list[dict] = []    # [{bucket, count}]


class AdminDashboardResponse(BaseModel):
    success: bool = True
    totals: dict  # {students, faculty, courses, departments, avg_performance, at_risk}
    performance_by_department: list[dict] = []
    risk_distribution: list[dict] = []
    attendance_distribution: list[dict] = []
    year_wise_performance: list[dict] = []
