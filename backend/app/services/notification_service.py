"""Notification service (§43) — thin re-export over ops_service so callers have a
dedicated domain module."""
from app.services.ops_service import list_for_user, mark_read, notify

__all__ = ["notify", "list_for_user", "mark_read"]
