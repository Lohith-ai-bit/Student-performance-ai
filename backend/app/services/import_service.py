"""CSV import pipeline (§20):

    Upload CSV -> validate columns -> validate data types -> detect invalid records
    -> preview -> confirm import -> insert into PostgreSQL

Invalid records are NEVER silently discarded — every problem is reported with
its row number and reason, and duplicates are counted, not re-inserted.

Expected columns (header, case-insensitive):
    student_id    (roll number, required)
    course        (course code, required)
    attendance    (percentage 0-100, optional)
    classes_conducted / classes_attended  (optional, overrides attendance %)
    quiz_score, assignment_score, midterm_score, endterm_score  (0-100, optional)
    date          (optional, YYYY-MM-DD; defaults to today for imported records)
"""
import csv
import io
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Assessment, Attendance, Course, Enrollment, Student
from app.models.enums import AssessmentType
from app.schemas.imports import CSVImportReport

REQUIRED_COLUMNS = {"student_id", "course"}
SCORE_COLUMNS = {
    "quiz_score": AssessmentType.QUIZ,
    "assignment_score": AssessmentType.ASSIGNMENT,
    "midterm_score": AssessmentType.MIDTERM,
    "endterm_score": AssessmentType.ENDTERM,
}


def _parse_number(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_and_validate(file_bytes: bytes, file_name: str, db: Session | None = None) -> tuple[list[dict], CSVImportReport]:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

    errors: list[dict] = []
    if not REQUIRED_COLUMNS.issubset(headers.keys()):
        missing = REQUIRED_COLUMNS - headers.keys()
        return [], CSVImportReport(
            success=False, file_name=file_name, total_rows=0, valid_rows=0, invalid_rows=0,
            inserted=0, skipped_duplicates=0,
            errors=[{"row": 0, "field": col, "message": f"Missing required column '{col}'", "raw": ""} for col in missing],
            message="CSV is missing required columns.",
        )

    rows: list[dict] = []
    data_row_count = 0
    for idx, raw in enumerate(reader, start=2):  # header is line 1
        data_row_count += 1
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
        row_errors: list[dict] = []

        roll = row.get("student_id", "")
        course_code = row.get("course", "")
        if not roll:
            row_errors.append({"row": idx, "field": "student_id", "message": "student_id is required", "raw": roll})
        if not course_code:
            row_errors.append({"row": idx, "field": "course", "message": "course is required", "raw": course_code})

        record_date = _parse_date(row.get("date", ""))
        if row.get("date") and record_date is None:
            row_errors.append({"row": idx, "field": "date", "message": "date must be YYYY-MM-DD", "raw": row.get("date")})

        attendance = _parse_number(row.get("attendance", ""))
        if attendance is not None and not (0 <= attendance <= 100):
            row_errors.append({"row": idx, "field": "attendance", "message": "attendance must be between 0 and 100", "raw": row.get("attendance")})

        conducted = _parse_number(row.get("classes_conducted", ""))
        attended = _parse_number(row.get("classes_attended", ""))
        if attended is not None and conducted is not None and attended > conducted:
            row_errors.append({"row": idx, "field": "classes_attended", "message": "classes_attended cannot exceed classes_conducted", "raw": row.get("classes_attended")})

        scores: dict[AssessmentType, float] = {}
        for col, a_type in SCORE_COLUMNS.items():
            value = _parse_number(row.get(col, ""))
            if value is None:
                if row.get(col):
                    row_errors.append({"row": idx, "field": col, "message": f"{col} must be a number", "raw": row.get(col)})
                continue
            if not (0 <= value <= 100):
                row_errors.append({"row": idx, "field": col, "message": f"{col} must be between 0 and 100", "raw": row.get(col)})
                continue
            scores[a_type] = value

        if row_errors:
            errors.extend(row_errors)
            continue

        rows.append(
            {
                "row_number": idx,
                "student_id": roll,
                "course": course_code,
                "attendance": attendance,
                "classes_conducted": int(conducted) if conducted is not None else None,
                "classes_attended": int(attended) if attended is not None else None,
                "scores": scores,
                "date": record_date or date.today(),
            }
        )

    # Existence validation (preview shows these before import when a DB session is provided)
    if db is not None and rows:
        rolls = {r["student_id"] for r in rows}
        codes = {r["course"].upper() for r in rows}
        known_rolls = {s.roll_number for s in db.query(Student).filter(Student.roll_number.in_(rolls)).all()}
        known_codes = {c.course_code.upper() for c in db.query(Course).filter(Course.course_code.in_(codes)).all()}
        still_valid: list[dict] = []
        for r_ in rows:
            if r_["student_id"] not in known_rolls:
                errors.append({"row": r_["row_number"], "field": "student_id", "message": f"No student with roll number '{r_['student_id']}'", "raw": r_["student_id"]})
                continue
            if r_["course"].upper() not in known_codes:
                errors.append({"row": r_["row_number"], "field": "course", "message": f"No course with code '{r_['course']}'", "raw": r_["course"]})
                continue
            still_valid.append(r_)
        rows = still_valid

    report = CSVImportReport(
        success=True,
        file_name=file_name,
        total_rows=data_row_count,
        valid_rows=len(rows),
        invalid_rows=data_row_count - len(rows),
        inserted=0,
        skipped_duplicates=0,
        errors=errors,
        message="Preview ready. Review the report and confirm to import valid rows.",
    )
    return rows, report


def import_rows(db: Session, rows: list[dict], file_name: str, invalid_count: int) -> CSVImportReport:
    inserted = 0
    skipped_duplicates = 0
    errors: list[dict] = []

    rolls = {r["student_id"] for r in rows}
    codes = {r["course"] for r in rows}
    students = {s.roll_number: s for s in db.query(Student).filter(Student.roll_number.in_(rolls)).all()}
    courses = {c.course_code.upper(): c for c in db.query(Course).filter(Course.course_code.in_({c.upper() for c in codes})).all()}

    for row in rows:
        student = students.get(row["student_id"])
        if student is None:
            errors.append({"row": row["row_number"], "field": "student_id", "message": f"No student with roll number '{row['student_id']}'", "raw": row["student_id"]})
            continue
        course = courses.get(row["course"].upper())
        if course is None:
            errors.append({"row": row["row_number"], "field": "course", "message": f"No course with code '{row['course']}'", "raw": row["course"]})
            continue

        # ensure enrollment (idempotent)
        academic_year = row["date"].year
        existing_enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student.id,
                Enrollment.course_id == course.id,
                Enrollment.academic_year == academic_year,
                Enrollment.semester == course.semester,
            )
            .first()
        )
        if existing_enrollment is None:
            db.add(Enrollment(student_id=student.id, course_id=course.id, academic_year=academic_year, semester=course.semester))

        # assessments (skip exact duplicates)
        for a_type, score in row["scores"].items():
            dup = (
                db.query(Assessment.id)
                .filter(
                    Assessment.student_id == student.id,
                    Assessment.course_id == course.id,
                    Assessment.assessment_type == a_type,
                    Assessment.assessment_date == row["date"],
                )
                .first()
            )
            if dup:
                skipped_duplicates += 1
                continue
            db.add(Assessment(student_id=student.id, course_id=course.id, assessment_type=a_type, score=score, maximum_score=100.0, assessment_date=row["date"]))
            inserted += 1

        # attendance
        if row["attendance"] is not None or row["classes_conducted"] is not None:
            if row["classes_conducted"] is not None and row["classes_attended"] is not None:
                conducted, attended = row["classes_conducted"], row["classes_attended"]
            else:
                # percentage-only import: store against a 100-class denominator (lossless for the %)
                conducted, attended = 100, int(round(row["attendance"]))
            dup = (
                db.query(Attendance.id)
                .filter(Attendance.student_id == student.id, Attendance.course_id == course.id, Attendance.date == row["date"])
                .first()
            )
            if dup:
                skipped_duplicates += 1
            else:
                from app.models.attendance import compute_attendance_percentage

                db.add(
                    Attendance(
                        student_id=student.id, course_id=course.id,
                        classes_conducted=conducted, classes_attended=attended,
                        attendance_percentage=compute_attendance_percentage(conducted, attended),
                        date=row["date"],
                    )
                )
                inserted += 1

    db.commit()
    return CSVImportReport(
        success=True,
        file_name=file_name,
        total_rows=len(rows) + invalid_count,
        valid_rows=len(rows),
        invalid_rows=invalid_count + len(errors),
        inserted=inserted,
        skipped_duplicates=skipped_duplicates,
        errors=errors,
        message=f"Import finished: {inserted} records inserted, {invalid_count + len(errors)} invalid rows reported, {skipped_duplicates} duplicates skipped.",
    )
