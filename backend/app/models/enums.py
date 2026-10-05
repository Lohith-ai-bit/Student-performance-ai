"""Shared enumerations (stored as strings in the DB for readability)."""
import enum


class Role(str, enum.Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"


class AssessmentType(str, enum.Enum):
    QUIZ = "QUIZ"
    ASSIGNMENT = "ASSIGNMENT"
    MIDTERM = "MIDTERM"
    ENDTERM = "ENDTERM"
    LAB = "LAB"
    PROJECT = "PROJECT"
    OTHER = "OTHER"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
