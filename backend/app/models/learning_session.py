"""Student learning sessions (§6.1): raw telemetry the sequence builder consumes."""
import uuid
from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, String, Time, Uuid, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.advanced_enums import SessionActivityType
from app.models.mixins import TimestampMixin


class LearningSession(TimestampMixin, Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_sessions_student_course_date", "student_id", "course_id", "session_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_type: Mapped[SessionActivityType] = mapped_column(
        String(20), nullable=False, default=SessionActivityType.OTHER.value
    )

    student: Mapped["Student"] = relationship()  # noqa: F821
    course: Mapped["Course"] = relationship()  # noqa: F821
