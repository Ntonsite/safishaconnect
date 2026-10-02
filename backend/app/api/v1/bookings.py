"""Customer booking endpoints. Every lookup is scoped to the signed-in customer."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Booking
from app.models.enums import TERMINAL_STATUSES, BookingStatus, RoleCode
from app.schemas.booking import BookingCreate, BookingDetail, BookingSummary, ReasonIn
from app.security.deps import CurrentCustomer, DbSession
from app.security.rate_limit import write_rate_limit
from app.services import booking_views
from app.services import bookings as booking_service
from app.services.lifecycle import Actor

router = APIRouter(prefix="/bookings", tags=["bookings"])

HISTORY = TERMINAL_STATUSES | {BookingStatus.CUSTOMER_CONFIRMED}


def _detail(db, booking: Booking) -> BookingDetail:
    return booking_views.detail(db, booking, RoleCode.CUSTOMER)


IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.:-]+$",
        description="Client-generated key (e.g. a UUID per booking attempt). Retrying with the same key "
        "returns the original booking instead of creating a duplicate.",
    ),
]


@router.post("", response_model=BookingDetail, status_code=status.HTTP_201_CREATED)
def create_booking(
    data: BookingCreate,
    customer: CurrentCustomer,
    db: DbSession,
    response: Response,
    idempotency_key: IdempotencyKey = None,
) -> BookingDetail:
    write_rate_limit(customer.user_id, "create-booking")
    if idempotency_key:
        existing = booking_service.find_by_idempotency_key(db, customer, idempotency_key)
        if existing is not None:
            return _replayed(db, response, booking_service.check_replay(existing, data))
    try:
        booking = booking_service.create_booking(db, customer, data, idempotency_key)
        db.commit()
    except IntegrityError as exc:
        # Lost a race with a concurrent request carrying the same key: return the winner's booking.
        db.rollback()
        existing = booking_service.find_by_idempotency_key(db, customer, idempotency_key) if idempotency_key else None
        if existing is None:
            raise exc
        return _replayed(db, response, booking_service.check_replay(existing, data))
    db.refresh(booking)
    return _detail(db, booking)


def _replayed(db, response: Response, booking: Booking) -> BookingDetail:
    response.status_code = status.HTTP_200_OK
    response.headers["Idempotent-Replayed"] = "true"
    return _detail(db, booking)


@router.get("", response_model=list[BookingSummary])
def my_bookings(
    customer: CurrentCustomer,
    db: DbSession,
    scope: Literal["all", "active", "history"] = "all",
    limit: int = Query(default=50, ge=1, le=200),
) -> list[BookingSummary]:
    stmt = select(Booking).where(Booking.customer_id == customer.id)
    if scope == "active":
        stmt = stmt.where(Booking.status.not_in(HISTORY))
    elif scope == "history":
        stmt = stmt.where(Booking.status.in_(HISTORY))
    stmt = stmt.order_by(Booking.scheduled_date.desc(), Booking.scheduled_start_time.desc()).limit(limit)
    return [booking_views.summary(b) for b in db.scalars(stmt).unique()]


@router.get("/{booking_id}", response_model=BookingDetail)
def get_booking(booking_id: uuid.UUID, customer: CurrentCustomer, db: DbSession) -> BookingDetail:
    return _detail(db, booking_service.get_customer_booking(db, customer, booking_id))


@router.post("/{booking_id}/confirm", response_model=BookingDetail)
def confirm_booking(booking_id: uuid.UUID, customer: CurrentCustomer, db: DbSession) -> BookingDetail:
    booking = booking_service.get_customer_booking(db, customer, booking_id, for_update=True)
    booking_service.confirm_booking(db, booking, customer.user, Actor.CUSTOMER)
    db.commit()
    return _detail(db, booking)


@router.post("/{booking_id}/cancel", response_model=BookingDetail)
def cancel_booking(booking_id: uuid.UUID, data: ReasonIn, customer: CurrentCustomer, db: DbSession) -> BookingDetail:
    booking = booking_service.get_customer_booking(db, customer, booking_id, for_update=True)
    booking_service.cancel_booking(db, booking, customer.user, Actor.CUSTOMER, data.reason)
    db.commit()
    return _detail(db, booking)


@router.post("/{booking_id}/confirm-completion", response_model=BookingDetail)
def confirm_completion(booking_id: uuid.UUID, customer: CurrentCustomer, db: DbSession) -> BookingDetail:
    booking = booking_service.get_customer_booking(db, customer, booking_id, for_update=True)
    booking_service.customer_confirm_completion(db, booking, customer.user)
    db.commit()
    return _detail(db, booking)
