"""CSV import request/report schemas (§20). Invalid records are reported, never silently dropped."""
from pydantic import BaseModel, Field


class CSVImportReport(BaseModel):
    success: bool = True
    file_name: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted: int
    skipped_duplicates: int
    errors: list[dict] = Field(default_factory=list)  # [{row, field, message, raw}]
    message: str
