"""Shared enumerations for the advanced (Phase 2/3) system."""
import enum


class SessionActivityType(str, enum.Enum):
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    QUIZ = "QUIZ"
    PRACTICE = "PRACTICE"
    ASSIGNMENT = "ASSIGNMENT"
    LECTURE = "LECTURE"
    OTHER = "OTHER"


class ModelType(str, enum.Enum):
    BASELINE = "BASELINE"
    TRANSFORMER = "TRANSFORMER"
    HYBRID = "HYBRID"


class ModelStatus(str, enum.Enum):
    TRAINING = "TRAINING"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class ExplanationMethod(str, enum.Enum):
    SHAP = "SHAP"
    LIME = "LIME"


class ResourceType(str, enum.Enum):
    VIDEO = "VIDEO"
    ARTICLE = "ARTICLE"
    DOCUMENT = "DOCUMENT"
    QUIZ = "QUIZ"
    PRACTICE = "PRACTICE"
    ASSIGNMENT = "ASSIGNMENT"


class RecommendationType(str, enum.Enum):
    CONTENT = "CONTENT"
    PRACTICE = "PRACTICE"
    REVISION = "REVISION"
    ATTENDANCE = "ATTENDANCE"
    TIME_MANAGEMENT = "TIME_MANAGEMENT"
    ASSESSMENT = "ASSESSMENT"
    FACULTY_INTERVENTION = "FACULTY_INTERVENTION"


class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class InterventionType(str, enum.Enum):
    COUNSELING = "COUNSELING"
    EXTRA_TUTORING = "EXTRA_TUTORING"
    PARENT_CONTACT = "PARENT_CONTACT"
    STUDY_PLAN = "STUDY_PLAN"
    MENTORING = "MENTORING"
    OTHER = "OTHER"


class BatchJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
