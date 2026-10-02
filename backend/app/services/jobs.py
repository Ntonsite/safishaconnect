"""Background jobs: expire stale job offers, deliver queued external notifications.

All job state lives in PostgreSQL, so nothing is lost when a process restarts and
any number of runners can work side by side:

* each unit of work runs in its own short transaction (one booking / one message),
* rows are claimed with ``FOR UPDATE SKIP LOCKED``, so runners never block each
  other or user requests.

Production runs these in the dedicated worker (``python -m app.worker``). For local
development they can also run inside the API process (``BACKGROUND_JOBS_ENABLED``).
"""

import asyncio
import contextlib

from starlette.concurrency import run_in_threadpool

from app.core import metrics
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.assignment import due_offers, expire_offer
from app.services.notifications import deliver_due_notifications

log = get_logger("jobs")


def run_expiry_once(limit: int = 200) -> int:
    """Expire every offer past its deadline (re-dispatching its booking). Returns how many."""
    expired = 0
    with SessionLocal() as db:
        work = due_offers(db, limit)
        db.rollback()  # release the snapshot; each offer gets its own transaction below
        for assignment_id, booking_id in work:
            try:
                if expire_offer(db, assignment_id, booking_id):
                    expired += 1
                db.commit()
            except Exception:
                db.rollback()
                log.exception("jobs.offer_expiry_item_failed", extra={"assignment_id": str(assignment_id)})
    return expired


def run_notification_delivery_once(limit: int = 100) -> int:
    with SessionLocal() as db:
        return deliver_due_notifications(db, limit)


JOBS = {
    "offer_expiry": run_expiry_once,
    "notification_delivery": run_notification_delivery_once,
}


def run_all_once() -> dict[str, int]:
    """One pass of every job. A failing job is logged and counted; the others still run."""
    results: dict[str, int] = {}
    for name, job in JOBS.items():
        try:
            results[name] = job()
            metrics.job_succeeded(name)
            if results[name]:
                log.info("jobs.completed", extra={"job": name, "count": results[name]})
        except Exception:
            metrics.job_failed(name)
            log.exception("jobs.failed", extra={"job": name})
    return results


async def background_loop(stop: asyncio.Event) -> None:
    """In-process runner used when BACKGROUND_JOBS_ENABLED=true (local development)."""
    interval = get_settings().worker_interval_seconds
    while not stop.is_set():
        await run_in_threadpool(run_all_once)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
