"""Learning resources (§6.6) and recommendations (§6.7) + feedback (§6.8)."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.advanced_enums import RecommendationStatus, RecommendationType, ResourceType
from app.models.mixins import TimestampMixin


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    resource_type: Mapped[ResourceType] = mapped_column(String(20), nullable=False)
    topic: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="BEGINNER")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    course: Mapped["Course | None"] = relationship()  # noqa: F821


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_student_status", "student_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="SET NULL"), index=True, nullable=True
    )
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("predictions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    recommendation_type: Mapped[RecommendationType] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1 (highest) .. 5
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # ranking score
    status: Mapped[RecommendationStatus] = mapped_column(String(20), nullable=False, default=RecommendationStatus.PENDING.value)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("learning_resources.id", ondelete="SET NULL"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped["Student"] = relationship()  # noqa: F821
    resource: Mapped["LearningResource | None"] = relationship()  # noqa: F821
    feedback: Mapped[list["RecommendationFeedback"]] = relationship(  # noqa: F821
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recommendations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1..5
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="feedback")  # noqa: F821
