"""Phase 2/3 API schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskLevel


class PredictAdvancedRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None
    explain: bool = True
    recommend: bool = True


class PredictionAdvancedResponse(BaseModel):
    success: bool = True
    student_id: str
    course_id: str | None
    predicted_score: float
    risk_probability: float
    risk_level: RiskLevel
    model_name: str
    model_version: str
    model_type: str
    prediction_id: str
    latency_ms: float
    explanation: dict | None = None
    recommendations_created: int | None = None


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_name: str
    model_type: str
    version: str
    dataset_version: str
    feature_version: str
    training_date: datetime
    metrics: dict
    hyperparameters: dict
    artifact_location: str
    status: str
    notes: str | None = None


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    experiment_name: str
    model_type: str
    dataset_version: str
    hyperparameters: dict
    metrics: dict
    training_duration_seconds: float | None
    notes: str | None
    created_at: datetime


class ExplanationFactor(BaseModel):
    feature: str
    label: str
    importance: float
    direction: str
    explanation_text: str = ""


class ExplanationResponse(BaseModel):
    success: bool = True
    prediction: dict
    shap: list[ExplanationFactor] = []
    lime: list[ExplanationFactor] = []
    gradient: list[ExplanationFactor] = []
    summary: str = ""
    factors: list[ExplanationFactor] = []
    disclaimer: str = ""


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID | None
    prediction_id: uuid.UUID | None
    recommendation_type: str
    title: str
    description: str
    reason: str
    priority: int
    confidence: float
    score: float
    status: str
    resource_id: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None


class RecommendationUpdate(BaseModel):
    status: str = Field(pattern="^(PENDING|IN_PROGRESS|COMPLETED|DISMISSED)$")


class RecommendationFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    helpful: bool | None = None
    feedback_text: str | None = Field(default=None, max_length=2000)


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID | None
    title: str
    description: str | None
    resource_type: str
    topic: str
    difficulty: str
    url: str
    estimated_minutes: int


class InterventionCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None
    prediction_id: uuid.UUID | None = None
    note: str = Field(min_length=5, max_length=4000)
    intervention_type: str = "OTHER"


class BatchPredictionRequest(BaseModel):
    scope: str = Field(pattern="^(STUDENT|COURSE|CLASS|DEPARTMENT)$")
    scope_id: str | None = None
    model_type: str = "BASELINE"
    model_version: str | None = None
    run_inline: bool = False  # small batches can run synchronously


class BatchJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scope: str
    scope_id: str | None
    model_type: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    result: dict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    notification_type: str
    link: str | None
    is_read: bool
    created_at: datetime


class DriftFeature(BaseModel):
    feature: str
    psi: float
    status: str
    training_mean: float | None
    live_mean: float | None


class DriftResponse(BaseModel):
    success: bool = True
    status: str
    features: list[DriftFeature] = []
    latency: dict = {}
    message: str = ""


class MonitoringResponse(BaseModel):
    success: bool = True
    summary: dict
    drift: dict
