"""In-process domain events, delivered only after the business transaction commits.

Services call :func:`publish` while they work. Events are parked on the SQLAlchemy
session and handed to subscribers *after* ``COMMIT`` succeeds; a rollback discards
them. Subscribers therefore never observe a booking that does not exist, and a
failing subscriber can never undo or break the business operation.

Today's subscribers are metrics and structured logs. A future outbox/Kafka bridge,
CRM sync or analytics feed subscribes here without touching booking, assignment or
payment code. See docs/architecture/ADR-004-kafka.md.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.logging import get_logger

log = get_logger("events")

# Canonical event names (dotted, past tense) — also the future topic/routing keys.
BOOKING_CREATED = "booking.created"
BOOKING_CANCELLED = "booking.cancelled"
ASSIGNMENT_OFFERED = "provider.assignment.requested"
ASSIGNMENT_ACCEPTED = "provider.assigned"
ASSIGNMENT_REJECTED = "provider.assignment.rejected"
ASSIGNMENT_EXPIRED = "provider.assignment.expired"
ASSIGNMENT_UNMATCHED = "provider.assignment.unmatched"
BOOKING_STATUS_CHANGED = "booking.status_changed"
PAYMENT_CONFIRMED = "payment.completed"
PAYMENT_GATEWAY_EVENT = "payment.gateway_event_received"
SETTLEMENT_SETTLED = "settlement.settled"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    data: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


Handler = Callable[[DomainEvent], None]
_handlers: dict[str, list[Handler]] = defaultdict(list)
_PENDING = "safisha_pending_events"


def subscribe(name: str, handler: Handler) -> None:
    """Register ``handler`` for an event name, or ``"*"`` for every event."""
    _handlers[name].append(handler)


def publish(db: Session, name: str, **data: Any) -> None:
    # Pin the event to a real transaction so a later rollback is guaranteed to discard it.
    db.connection()
    db.info.setdefault(_PENDING, []).append(DomainEvent(name, data))


def _dispatch(evt: DomainEvent) -> None:
    for handler in (*_handlers.get(evt.name, ()), *_handlers.get("*", ())):
        try:
            handler(evt)
        except Exception:  # a subscriber must never affect the committed business operation
            log.exception("events.handler_failed", extra={"event_name": evt.name})


@event.listens_for(Session, "after_commit")
def _after_commit(session: Session) -> None:
    for evt in session.info.pop(_PENDING, []):
        _dispatch(evt)


@event.listens_for(Session, "after_soft_rollback")
def _after_rollback(session: Session, _previous_transaction) -> None:
    session.info.pop(_PENDING, None)


def _log_event(evt: DomainEvent) -> None:
    log.info("domain_event", extra={"event_name": evt.name, **{f"e_{k}": v for k, v in evt.data.items()}})


subscribe("*", _log_event)
