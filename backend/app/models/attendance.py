import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Uuid, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


def compute_attendance_percentage(classes_conducted: int, classes_attended: int) -> float:
    """Single source of truth — the client-provided percentage is never trusted."""
    if classes_conducted <= 0:
        return 0.0
    return round((classes_attended / classes_conducted) * 100.0, 2)


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("classes_attended <= classes_conducted", name="ck_attendance_counts"),
        CheckConstraint("classes_conducted >= 0 AND classes_attended >= 0", name="ck_attendance_nonneg"),
        Index("ix_attendance_student_course_date", "student_id", "course_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    classes_conducted: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    classes_attended: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    attendance_percentage: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0"))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    student: Mapped["Student"] = relationship(back_populates="attendance")  # noqa: F821
    course: Mapped["Course"] = relationship(back_populates="attendance")  # noqa: F821
