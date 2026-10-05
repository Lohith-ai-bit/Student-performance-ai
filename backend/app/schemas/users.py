import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    roll_number: str
    department: str
    branch: str
    year: int
    semester: int
    section: str
    admission_year: int


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    roll_number: str = Field(min_length=1, max_length=50)
    department: str = Field(min_length=2, max_length=120)
    branch: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1, le=6)
    semester: int = Field(ge=1, le=12)
    section: str = Field(min_length=1, max_length=10)
    admission_year: int | None = Field(default=None, ge=2000, le=2100)


class StudentUpdate(BaseModel):
    department: str | None = Field(default=None, min_length=2, max_length=120)
    branch: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = Field(default=None, ge=1, le=6)
    semester: int | None = Field(default=None, ge=1, le=12)
    section: str | None = Field(default=None, min_length=1, max_length=10)


class StudentOut(StudentProfileOut):
    name: str
    email: EmailStr


class FacultyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    employee_id: str = Field(min_length=1, max_length=50)
    department: str = Field(min_length=2, max_length=120)
    designation: str = Field(min_length=1, max_length=120)
    course_ids: list[uuid.UUID] = []


class FacultyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    employee_id: str
    department: str
    designation: str
    course_ids: list[uuid.UUID] = []


class FacultyUpdate(BaseModel):
    department: str | None = Field(default=None, min_length=2, max_length=120)
    designation: str | None = Field(default=None, min_length=1, max_length=120)
    course_ids: list[uuid.UUID] | None = None
    is_active: bool | None = None
