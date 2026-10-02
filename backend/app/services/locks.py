"""Row-level locking for concurrency-sensitive operations.

Locking strategy (see docs/PRODUCTION_ARCHITECTURE.md, "Concurrency strategy"):

* **Booking row** — every operation that changes a booking, its assignments, its payment
  or its settlement first locks the booking row. One booking therefore changes through
  exactly one transaction at a time (accept vs. cancel vs. expiry vs. admin...).
* **Provider row** — taken *after* the booking lock whenever a provider's capacity is
  checked and consumed (accepting/assigning/offering a job), so two different bookings
  cannot both claim the same free slot of the same provider.

Lock order is always booking -> provider, which rules out lock-order deadlocks. The
dispatcher, which may try several providers, uses ``SKIP LOCKED`` on providers so it never
waits behind another transaction. ``FOR NO KEY UPDATE`` is used instead of ``FOR UPDATE``
so inserts referencing the row (status history, notifications, assignments) are not blocked.

Locks are held only until the end of the request's transaction, and ``lock_timeout``
(DB_LOCK_TIMEOUT_MS) bounds every wait. No table is ever locked.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Booking, Provider


def lock_booking(db: Session, booking_id: uuid.UUID, *, skip_locked: bool = False) -> Booking | None:
    """Lock and *re-read* a booking. Returns None only when ``skip_locked`` and it is busy."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update(of=Booking, key_share=True, skip_locked=skip_locked)
        .execution_options(populate_existing=True)  # never decide on a stale identity-map copy
    )
    booking = db.scalars(stmt).unique().one_or_none()
    if booking is None and not skip_locked:
        raise NotFoundError("Booking not found.")
    return booking


def lock_provider(db: Session, provider_id: uuid.UUID, *, skip_locked: bool = False) -> Provider | None:
    stmt = (
        select(Provider)
        .where(Provider.id == provider_id)
        .with_for_update(of=Provider, key_share=True, skip_locked=skip_locked)
        .execution_options(populate_existing=True)
    )
    return db.scalars(stmt).unique().one_or_none()
