from datetime import datetime

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RiskLevel


class PredictRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def at_least_one_scope(self):
        # course_id optional: None => aggregate prediction across all courses
        return self


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID | None
    model_name: str
    model_version: str
    predicted_score: float
    risk_probability: float
    risk_level: RiskLevel
    prediction_date: datetime
    created_at: datetime


class PredictionResponse(BaseModel):
    success: bool = True
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None
    predicted_score: float
    risk_probability: float
    risk_level: RiskLevel
    model_name: str
    model_version: str
    prediction_id: str


class ModelInfo(BaseModel):
    model_name: str
    model_version: str
    task: str
    trained_at: datetime | None = None
    dataset_version: str | None = None
    feature_version: str | None = None
    metrics: dict = {}
    selected: bool = False


class ModelsResponse(BaseModel):
    success: bool = True
    models: list[ModelInfo] = []


class EvaluationRow(BaseModel):
    model_name: str
    task: str
    metrics: dict


class EvaluationResponse(BaseModel):
    success: bool = True
    evaluations: list[EvaluationRow] = []
