import uuid
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Uuid, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AssessmentType
from app.models.mixins import TimestampMixin


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        Index("ix_assessments_student_course_date", "student_id", "course_id", "assessment_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessment_type", native_enum=False, length=20), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    student: Mapped["Student"] = relationship(back_populates="assessments")  # noqa: F821
    course: Mapped["Course"] = relationship(back_populates="assessments")  # noqa: F821
