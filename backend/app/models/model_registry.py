"""Model registry (§6.3/§6.4/§17) — versioned, reproducible, experiment-backed."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.advanced_enums import ModelStatus, ModelType
from app.models.mixins import TimestampMixin


class ModelVersion(TimestampMixin, Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(String(20), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(40), nullable=False)
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    artifact_location: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ModelStatus] = mapped_column(String(20), nullable=False, default=ModelStatus.TRAINING.value, index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class ModelExperiment(TimestampMixin, Base):
    __tablename__ = "model_experiments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    experiment_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    model_type: Mapped[ModelType] = mapped_column(String(20), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    training_duration_seconds: Mapped[float] = mapped_column(nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
