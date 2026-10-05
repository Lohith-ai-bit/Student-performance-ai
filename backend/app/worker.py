"""Background worker (§42): consumes batch-prediction jobs from the Redis queue.

Run as its own container (see docker-compose `worker` service):
    python -m app.worker

Also processes any job directly by id: python -m app.worker --job-id <uuid>
"""
import argparse
import sys
import time
import uuid
from pathlib import Path

import redis

from app.core.config import settings

QUEUE_KEY = "spa:batch_jobs"


def pop_job(timeout: int = 5) -> str | None:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
    item = client.blpop(QUEUE_KEY, timeout=timeout)
    return item[1].decode() if item else None


def run_job(job_id: str) -> None:
    from app.core.database import SessionLocal
    from app.services import ops_service

    with SessionLocal() as db:
        job = ops_service.process_batch_job(db, uuid.UUID(job_id))
        print(f"[worker] job {job_id}: status={job.status} processed={job.processed_items}/{job.total_items} failed={job.failed_items}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-prediction background worker")
    parser.add_argument("--job-id", default=None, help="Process one job directly and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    if args.job_id:
        run_job(args.job_id)
        return

    print(f"[worker] listening on Redis queue '{QUEUE_KEY}' (redis: {settings.REDIS_URL})")
    while True:
        try:
            job_id = pop_job(timeout=5)
            if job_id:
                run_job(job_id)
        except KeyboardInterrupt:
            print("[worker] shutting down")
            sys.exit(0)
        except redis.exceptions.ConnectionError:
            print(f"[worker] Redis unavailable, retrying in {args.poll_seconds}s…")
            time.sleep(args.poll_seconds)
        except Exception as exc:  # keep the worker alive on per-job failures
            print(f"[worker] job failed: {exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
