from datetime import datetime

import uuid

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=20)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    created_at: datetime


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=2, max_length=30)
    course_name: str = Field(min_length=2, max_length=200)
    credits: int = Field(ge=1, le=10)
    department_id: uuid.UUID | None = None
    semester: int = Field(ge=1, le=12)


class CourseUpdate(BaseModel):
    course_name: str | None = Field(default=None, min_length=2, max_length=200)
    credits: int | None = Field(default=None, ge=1, le=10)
    department_id: uuid.UUID | None = None
    semester: int | None = Field(default=None, ge=1, le=12)


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_code: str
    course_name: str
    credits: int
    department_id: uuid.UUID | None
    semester: int


class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    academic_year: int = Field(ge=2000, le=2100)
    semester: int = Field(ge=1, le=12)


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    academic_year: int
    semester: int
