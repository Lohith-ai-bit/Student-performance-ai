"""Notifications (§43), batch prediction jobs (§41/§42), audit logs (§48)."""
import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog, BatchPredictionJob, Notification
from app.models.advanced_enums import BatchJobStatus


# ---------------------------------------------------------------- notifications
def notify(db: Session, recipient_id: uuid.UUID, title: str, message: str, notification_type: str, link: str | None = None) -> Notification:
    row = Notification(
        recipient_id=recipient_id, title=title, message=message,
        notification_type=notification_type, link=link,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_user(db: Session, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.recipient_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID | None = None) -> int:
    query = db.query(Notification).filter(Notification.recipient_id == user_id, Notification.is_read.is_(False))
    if notification_id:
        query = query.filter(Notification.id == notification_id)
    count = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return count


# ------------------------------------------------------------- batch prediction
def create_batch_job(
    db: Session, requested_by: uuid.UUID, scope: str, scope_id: str | None,
    model_type: str, model_version: str | None, total_items: int,
) -> BatchPredictionJob:
    job = BatchPredictionJob(
        requested_by=requested_by, scope=scope.upper(), scope_id=scope_id,
        model_type=model_type.upper(), model_version=model_version,
        status=BatchJobStatus.QUEUED.value, total_items=total_items,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def enqueue_batch_job(job_id: uuid.UUID) -> None:
    """Push the job onto the Redis queue consumed by the background worker."""
    try:
        from app.core.config import settings

        import redis

        client = redis.Redis.from_url(settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "redis://localhost:6379/0", socket_connect_timeout=2)
        client.rpush("spa:batch_jobs", str(job_id))
    except Exception:
        # Redis unavailable: the worker script can also run jobs directly by id;
        # the job stays QUEUED and the inline fallback below handles small batches.
        pass


def process_batch_job(db: Session, job_id: uuid.UUID, inline_limit: int = 60) -> BatchPredictionJob:
    """Execute a batch job synchronously (worker path, or inline for small batches)."""
    from app.core.errors import NotFoundError
    from app.models import Course, Department, Enrollment, Student
    from ml.inference.engine import predict as engine_predict

    job = db.get(BatchPredictionJob, job_id)
    if job is None:
        raise NotFoundError("Batch job could not be found.", code="JOB_NOT_FOUND")
    if job.status == BatchJobStatus.RUNNING.value:
        return job

    job.status = BatchJobStatus.RUNNING.value
    from datetime import datetime, timezone

    job.started_at = datetime.now(timezone.utc)
    db.commit()

    # resolve the student list for the scope
    students: list[Student] = []
    if job.scope == "STUDENT":
        student = db.get(Student, uuid.UUID(job.scope_id))
        students = [student] if student else []
    elif job.scope == "COURSE":
        course = db.get(Course, uuid.UUID(job.scope_id)) if job.scope_id else None
        if course:
            students = (
                db.query(Student).join(Enrollment, Enrollment.student_id == Student.id)
                .filter(Enrollment.course_id == course.id).all()
            )
    elif job.scope == "DEPARTMENT":
        students = db.query(Student).filter(Student.department == job.scope_id).all()
    elif job.scope == "CLASS":
        year, semester, section, department = job.scope_id.split("|")
        students = (
            db.query(Student)
            .filter(
                Student.year == int(year), Student.semester == int(semester),
                Student.section == section, Student.department == department,
            )
            .all()
        )
    else:
        students = db.query(Student).all()

    job.total_items = len(students)
    db.commit()

    from app.models import User

    requester = db.get(User, job.requested_by)
    results = []
    for student in students:
        try:
            result = engine_predict(
                db, student, None,
                model_type=job.model_type, model_version=job.model_version,
                persist=True, explain=False, recommend=False,
            )
            results.append(
                {
                    "student_id": str(student.id), "roll_number": student.roll_number,
                    "predicted_score": result["predicted_score"],
                    "risk_probability": result["risk_probability"],
                    "risk_level": result["risk_level"],
                }
            )
            job.processed_items += 1
        except Exception:
            job.failed_items += 1
        db.commit()

    job.status = BatchJobStatus.COMPLETED.value if job.failed_items < len(students) else BatchJobStatus.FAILED.value
    from datetime import datetime, timezone

    job.finished_at = datetime.now(timezone.utc)
    job.result = {"predictions": results[:500]}
    db.commit()
    return job


# ------------------------------------------------------------------- audit logs
def audit(db: Session, user_id: uuid.UUID | None, action: str, resource: str | None = None, detail: dict | None = None, ip: str | None = None) -> None:
    db.add(
        AuditLog(
            user_id=user_id, action=action, resource=resource,
            detail=detail or {}, ip_address=ip,
        )
    )
    db.commit()
