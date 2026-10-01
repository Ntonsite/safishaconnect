"""Explicit booking state machine.

Every status change goes through :func:`transition`, which validates the move
against ``TRANSITIONS`` for the acting party and records history.
"""

from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.errors import InvalidTransitionError
from app.core.logging import get_logger
from app.models import Booking, BookingStatusHistory, User
from app.models.enums import BookingStatus as S
from app.utils.clock import utcnow

log = get_logger("lifecycle")


class Actor(StrEnum):
    CUSTOMER = "CUSTOMER"
    PROVIDER = "PROVIDER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


C, P, A, SYS = Actor.CUSTOMER, Actor.PROVIDER, Actor.ADMIN, Actor.SYSTEM

TRANSITIONS: dict[tuple[S, S], frozenset[Actor]] = {
    (S.PENDING_CONFIRMATION, S.CONFIRMED): frozenset({C, A}),
    (S.CONFIRMED, S.FINDING_PROVIDER): frozenset({SYS, A}),
    (S.CONFIRMED, S.REASSIGNMENT_REQUIRED): frozenset({SYS}),
    (S.CONFIRMED, S.PROVIDER_ASSIGNED): frozenset({A}),
    (S.FINDING_PROVIDER, S.PROVIDER_ASSIGNED): frozenset({P, A}),
    (S.FINDING_PROVIDER, S.REASSIGNMENT_REQUIRED): frozenset({SYS, A}),
    (S.REASSIGNMENT_REQUIRED, S.FINDING_PROVIDER): frozenset({SYS, A}),
    (S.REASSIGNMENT_REQUIRED, S.PROVIDER_ASSIGNED): frozenset({P, A}),
    (S.PROVIDER_ASSIGNED, S.PROVIDER_EN_ROUTE): frozenset({P, A}),
    (S.PROVIDER_ASSIGNED, S.FINDING_PROVIDER): frozenset({P, A, SYS}),
    (S.PROVIDER_ASSIGNED, S.REASSIGNMENT_REQUIRED): frozenset({P, A, SYS}),
    (S.PROVIDER_ASSIGNED, S.PROVIDER_ASSIGNED): frozenset({A}),  # admin swaps provider
    (S.PROVIDER_EN_ROUTE, S.PROVIDER_ARRIVED): frozenset({P, A}),
    (S.PROVIDER_EN_ROUTE, S.FINDING_PROVIDER): frozenset({A}),
    (S.PROVIDER_EN_ROUTE, S.REASSIGNMENT_REQUIRED): frozenset({A, SYS}),
    (S.PROVIDER_EN_ROUTE, S.PROVIDER_ASSIGNED): frozenset({A}),
    (S.PROVIDER_ARRIVED, S.SERVICE_IN_PROGRESS): frozenset({P, A}),
    (S.SERVICE_IN_PROGRESS, S.COMPLETED_BY_PROVIDER): frozenset({P, A}),
    (S.COMPLETED_BY_PROVIDER, S.CUSTOMER_CONFIRMED): frozenset({C, A}),
    (S.COMPLETED_BY_PROVIDER, S.DISPUTED): frozenset({C, A}),
    (S.CUSTOMER_CONFIRMED, S.CLOSED): frozenset({SYS, A}),
    (S.DISPUTED, S.CUSTOMER_CONFIRMED): frozenset({A}),
    (S.DISPUTED, S.CLOSED): frozenset({A}),
    (S.DISPUTED, S.CANCELLED): frozenset({A}),
    # Cancellation
    (S.PENDING_CONFIRMATION, S.CANCELLED): frozenset({C, A}),
    (S.CONFIRMED, S.CANCELLED): frozenset({C, A}),
    (S.FINDING_PROVIDER, S.CANCELLED): frozenset({C, A}),
    (S.REASSIGNMENT_REQUIRED, S.CANCELLED): frozenset({C, A}),
    (S.PROVIDER_ASSIGNED, S.CANCELLED): frozenset({C, A}),
    (S.PROVIDER_EN_ROUTE, S.CANCELLED): frozenset({A}),
    (S.PROVIDER_ARRIVED, S.CANCELLED): frozenset({A}),
}

# Provider-driven operational steps, in order.
PROVIDER_PROGRESS: dict[S, S] = {
    S.PROVIDER_ASSIGNED: S.PROVIDER_EN_ROUTE,
    S.PROVIDER_EN_ROUTE: S.PROVIDER_ARRIVED,
    S.PROVIDER_ARRIVED: S.SERVICE_IN_PROGRESS,
    S.SERVICE_IN_PROGRESS: S.COMPLETED_BY_PROVIDER,
}


def can_transition(current: S, target: S, actor: Actor) -> bool:
    return actor in TRANSITIONS.get((current, target), frozenset())


def admin_targets(current: S) -> list[S]:
    return [to for (frm, to), actors in TRANSITIONS.items() if frm == current and A in actors and to != frm]


def transition(
    db: Session,
    booking: Booking,
    target: S,
    actor: Actor,
    user: User | None = None,
    note: str | None = None,
) -> None:
    current = booking.status
    if not can_transition(current, target, actor):
        raise InvalidTransitionError(
            f"Booking cannot move from {current} to {target}.",
            details={"from": current, "to": target},
        )
    now = utcnow()
    booking.status = target
    if target == S.CONFIRMED:
        booking.confirmed_at = now
    elif target == S.COMPLETED_BY_PROVIDER:
        booking.completed_at = now
    elif target == S.CUSTOMER_CONFIRMED:
        booking.customer_confirmed_at = now
    elif target == S.CLOSED:
        booking.closed_at = now
    elif target == S.CANCELLED:
        booking.cancelled_at = now
        booking.cancellation_reason = note
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=current,
            to_status=target,
            changed_by_id=user.id if user else None,
            note=note,
            created_at=now,
        )
    )
    log.info(
        "booking.status_changed",
        extra={"booking": booking.reference, "from": current, "to": target, "actor": actor},
    )
