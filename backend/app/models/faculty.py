import uuid

from sqlalchemy import Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

# Faculty-to-course assignment (supports "view assigned courses" RBAC).
faculty_courses = Table(
    "faculty_courses",
    Base.metadata,
    Column("faculty_id", Uuid, ForeignKey("faculty.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)


class Faculty(TimestampMixin, Base):
    __tablename__ = "faculty"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    designation: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped["User"] = relationship(back_populates="faculty")  # noqa: F821
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        secondary=faculty_courses, back_populates="faculty_members", lazy="selectin"
    )
