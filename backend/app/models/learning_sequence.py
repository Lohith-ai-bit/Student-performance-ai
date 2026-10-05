"""Persisted temporal learning sequences (§6.2). sequence_data is a JSON list of
per-week feature vectors — exactly what the Transformer consumes."""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Uuid, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class StudentLearningSequence(TimestampMixin, Base):
    __tablename__ = "student_learning_sequences"
    __table_args__ = (
        Index("ix_sequences_student_course_date", "student_id", "course_id", "sequence_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence_date: Mapped[date] = mapped_column(Date, nullable=False)
    sequence_data: Mapped[list] = mapped_column(JSON, nullable=False)  # [[week1...], [week2...], ...]
    sequence_length: Mapped[int] = mapped_column(Integer, nullable=False)

    student: Mapped["Student"] = relationship()  # noqa: F821
    course: Mapped["Course"] = relationship()  # noqa: F821
