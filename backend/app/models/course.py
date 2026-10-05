import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Course(TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("course_code", "semester", name="uq_course_code_semester"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_code: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    department: Mapped["Department | None"] = relationship(back_populates="courses")  # noqa: F821
    faculty_members: Mapped[list["Faculty"]] = relationship(  # noqa: F821
        secondary="faculty_courses", back_populates="courses"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(  # noqa: F821
        back_populates="course", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(  # noqa: F821
        back_populates="course", cascade="all, delete-orphan"
    )
    attendance: Mapped[list["Attendance"]] = relationship(  # noqa: F821
        back_populates="course", cascade="all, delete-orphan"
    )
    learning_activities: Mapped[list["LearningActivity"]] = relationship(  # noqa: F821
        back_populates="course", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(  # noqa: F821
        back_populates="course", cascade="all, delete-orphan"
    )
