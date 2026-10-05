from datetime import date, datetime

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AssessmentType


class AssessmentCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    assessment_type: AssessmentType
    score: float = Field(ge=0, le=1000)
    maximum_score: float = Field(gt=0, le=1000)
    assessment_date: date

    @model_validator(mode="after")
    def score_within_max(self):
        if self.score > self.maximum_score:
            raise ValueError("score cannot exceed maximum_score")
        return self


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    assessment_type: AssessmentType
    score: float
    maximum_score: float
    assessment_date: date
    created_at: datetime


class AttendanceCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    classes_conducted: int = Field(ge=0, le=1000)
    classes_attended: int = Field(ge=0, le=1000)
    date: date

    @model_validator(mode="after")
    def attended_not_over_conducted(self):
        if self.classes_attended > self.classes_conducted:
            raise ValueError("classes_attended cannot exceed classes_conducted")
        return self


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    classes_conducted: int
    classes_attended: int
    attendance_percentage: float
    date: date
    created_at: datetime


class LearningActivityCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    activity_date: date
    session_duration: int = Field(ge=0, le=1440, default=0)
    videos_watched: int = Field(ge=0, le=1000, default=0)
    videos_completed: int = Field(ge=0, le=1000, default=0)
    documents_opened: int = Field(ge=0, le=1000, default=0)
    quiz_attempts: int = Field(ge=0, le=1000, default=0)
    assignments_submitted: int = Field(ge=0, le=1000, default=0)
    late_submissions: int = Field(ge=0, le=1000, default=0)
    practice_questions_attempted: int = Field(ge=0, le=10000, default=0)
    login_count: int = Field(ge=0, le=100, default=0)

    @model_validator(mode="after")
    def completed_not_over_watched(self):
        if self.videos_completed > self.videos_watched:
            raise ValueError("videos_completed cannot exceed videos_watched")
        if self.late_submissions > self.assignments_submitted:
            raise ValueError("late_submissions cannot exceed assignments_submitted")
        return self


class LearningActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    activity_date: date
    session_duration: int
    videos_watched: int
    videos_completed: int
    documents_opened: int
    quiz_attempts: int
    assignments_submitted: int
    late_submissions: int
    practice_questions_attempted: int
    login_count: int
    created_at: datetime
