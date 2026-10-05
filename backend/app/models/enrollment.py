import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Enrollment(TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "academic_year", "semester", name="uq_enrollment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    enrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="enrollments")  # noqa: F821
    course: Mapped["Course"] = relationship(back_populates="enrollments")  # noqa: F821
