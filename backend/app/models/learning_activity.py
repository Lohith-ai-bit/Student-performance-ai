"""Daily learning-behaviour telemetry.

This table becomes one of the inputs to the Transformer in Phase 2, which is
why it is kept as a time series (one row per student/course/day).
"""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Uuid, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class LearningActivity(TimestampMixin, Base):
    __tablename__ = "learning_activities"
    __table_args__ = (
        Index("ix_activities_student_course_date", "student_id", "course_id", "activity_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # minutes
    videos_watched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quiz_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignments_submitted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    practice_questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    student: Mapped["Student"] = relationship(back_populates="learning_activities")  # noqa: F821
    course: Mapped["Course"] = relationship(back_populates="learning_activities")  # noqa: F821
