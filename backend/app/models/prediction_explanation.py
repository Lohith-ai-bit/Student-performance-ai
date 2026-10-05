"""Per-prediction explanations (§6.5) — SHAP/LIME factors with human-readable text."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.advanced_enums import ExplanationMethod


class PredictionExplanation(Base):
    __tablename__ = "prediction_explanations"
    __table_args__ = (Index("ix_explanations_prediction_method", "prediction_id", "method"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("predictions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    method: Mapped[ExplanationMethod] = mapped_column(String(10), nullable=False)
    feature: Mapped[str] = mapped_column(String(120), nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "positive" | "negative"
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    prediction: Mapped["Prediction"] = relationship()  # noqa: F821
