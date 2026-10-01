"""Lightweight in-process background job: expire stale job offers and re-dispatch.

Runs inside the API process for MVP simplicity. ``FOR UPDATE SKIP LOCKED`` keeps it
safe if several API replicas run it concurrently; move to a dedicated worker later.
"""

import asyncio
import contextlib

from starlette.concurrency import run_in_threadpool

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.assignment import expire_stale_offers

log = get_logger("jobs")
INTERVAL_SECONDS = 60


def run_expiry_once() -> int:
    with SessionLocal() as db:
        try:
            count = expire_stale_offers(db)
            db.commit()
            return count
        except Exception:
            db.rollback()
            raise


async def offer_expiry_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            expired = await run_in_threadpool(run_expiry_once)
            if expired:
                log.info("jobs.offers_expired", extra={"count": expired})
        except Exception:
            log.exception("jobs.offer_expiry_failed")
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=INTERVAL_SECONDS)
