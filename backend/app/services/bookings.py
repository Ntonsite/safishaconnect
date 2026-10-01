"""Booking use-cases: create, confirm, cancel, progress, complete."""

import secrets
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.logging import get_logger
from app.models import Booking, BookingPriceItem, BookingStatusHistory, Customer, Provider, ServiceArea, User
from app.models.enums import BookingStatus, RoleCode
from app.schemas.booking import AvailabilityOut, BookingCreate, SlotOut
from app.services import assignment, payments, platform_settings
from app.services.lifecycle import PROVIDER_PROGRESS, Actor, transition
from app.services.notifications import notify
from app.services.pricing import Quote, calculate_quote, split_commission
from app.utils.clock import add_minutes, local_now, local_today, to_local_datetime, utcnow

log = get_logger("bookings")

_REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion


def new_reference(db: Session) -> str:
    while True:
        ref = "SC-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))
        if not db.scalar(select(Booking.id).where(Booking.reference == ref)):
            return ref


def validate_schedule(db: Session, day: date, start: time, duration_minutes: int) -> None:
    settings = get_settings()
    if start.minute % 30 or start.second:
        raise ValidationFailedError("Please choose a start time on the hour or half hour.", code="INVALID_TIME")
    if not (settings.booking_slot_start_hour <= start.hour <= settings.booking_slot_end_hour):
        raise ValidationFailedError(
            f"Start time must be between {settings.booking_slot_start_hour:02d}:00 and "
            f"{settings.booking_slot_end_hour:02d}:00.",
            code="INVALID_TIME",
        )
    if start.hour * 60 + start.minute + duration_minutes > 22 * 60:
        raise ValidationFailedError("This job would run too late. Please choose an earlier time.", code="INVALID_TIME")
    lead = timedelta(hours=platform_settings.min_lead_hours(db))
    if to_local_datetime(day, start) < local_now() + lead:
        raise ValidationFailedError(
            f"Bookings need at least {platform_settings.min_lead_hours(db)} hours' notice.", code="TOO_SOON"
        )
    if day > local_today() + timedelta(days=platform_settings.max_days_ahead(db)):
        raise ValidationFailedError("That date is too far ahead.", code="TOO_FAR_AHEAD")


def _active_area(db: Session, area_id) -> ServiceArea:
    area = db.get(ServiceArea, area_id)
    if area is None or not area.is_active or not area.city.is_active:
        raise ValidationFailedError("We don't serve this area yet.", code="AREA_NOT_SERVED")
    return area


def slots(db: Session, service_id, area_id, day: date, duration_minutes: int) -> AvailabilityOut:
    """Start times for a day, each flagged with whether an eligible provider is free."""
    settings = get_settings()
    _active_area(db, area_id)
    out: list[SlotOut] = []
    for hour in range(settings.booking_slot_start_hour, settings.booking_slot_end_hour + 1):
        start = time(hour, 0)
        try:
            validate_schedule(db, day, start, duration_minutes)
            spec = assignment.JobSpec(service_id, area_id, day, start, duration_minutes)
            available = bool(assignment.find_eligible(db, spec))
        except ValidationFailedError:
            available = False
        out.append(SlotOut(start_time=start, end_time=add_minutes(start, duration_minutes), available=available))
    return AvailabilityOut(date=day, duration_minutes=duration_minutes, slots=out)


def price_items_from_quote(quote: Quote) -> list[BookingPriceItem]:
    return [
        BookingPriceItem(
            position=i,
            kind=ln.kind,
            code=ln.code,
            label_en=ln.label_en,
            label_sw=ln.label_sw,
            option_id=ln.option_id,
            quantity=ln.quantity,
            unit_amount=ln.unit_amount,
            amount=ln.amount,
        )
        for i, ln in enumerate(quote.lines)
    ]


def create_booking(db: Session, customer: Customer, data: BookingCreate) -> Booking:
    area = _active_area(db, data.area_id)
    payments.ensure_method_available(data.payment_method)
    quote = calculate_quote(db, data)
    validate_schedule(db, data.scheduled_date, data.scheduled_start_time, quote.duration_minutes)
    economics = split_commission(quote.total_amount, platform_settings.commission_percent(db))

    booking = Booking(
        reference=new_reference(db),
        customer_id=customer.id,
        service_id=quote.service.id,
        area_id=area.id,
        status=BookingStatus.PENDING_CONFIRMATION,
        address_line=data.address_line,
        landmark=data.landmark,
        property_type_option_id=quote.property_type.id if quote.property_type else None,
        size_option_id=quote.size.id if quote.size else None,
        bedrooms=quote.bedrooms,
        bathrooms=quote.bathrooms,
        special_instructions=data.special_instructions,
        scheduled_date=data.scheduled_date,
        scheduled_start_time=data.scheduled_start_time,
        estimated_duration_minutes=quote.duration_minutes,
        currency=quote.currency,
        service_name_snapshot=quote.service.name_en,
        base_amount=quote.base_amount,
        adjustments_amount=quote.adjustments_amount,
        total_amount=quote.total_amount,
        commission_percent=economics.commission_percent,
        commission_amount=economics.commission_amount,
        provider_earning=economics.provider_earning,
        payment_method=data.payment_method,
        price_items=price_items_from_quote(quote),
    )
    db.add(booking)
    db.flush()
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=None,
            to_status=BookingStatus.PENDING_CONFIRMATION,
            changed_by_id=customer.user_id,
            note="Booking created",
            created_at=utcnow(),
        )
    )
    payments.create_payment(db, booking)
    if not customer.default_area_id:
        customer.default_area_id = area.id
        customer.default_address = data.address_line
    log.info("booking.created", extra={"booking": booking.reference, "total": str(booking.total_amount)})
    db.flush()
    db.refresh(booking)
    if data.confirm:
        confirm_booking(db, booking, customer.user, Actor.CUSTOMER)
    else:
        notify(db, customer.user_id, "BOOKING_RECEIVED", booking)
    return booking


def confirm_booking(db: Session, booking: Booking, user: User, actor: Actor) -> None:
    if booking.status == BookingStatus.PENDING_CONFIRMATION:
        # Re-check the schedule: a pending booking may have gone stale.
        validate_schedule(db, booking.scheduled_date, booking.scheduled_start_time, booking.estimated_duration_minutes)
    transition(db, booking, BookingStatus.CONFIRMED, actor, user)
    notify(db, booking.customer.user_id, "BOOKING_CONFIRMED", booking)
    assignment.dispatch(db, booking)


def cancel_booking(db: Session, booking: Booking, user: User, actor: Actor, reason: str | None) -> None:
    transition(db, booking, BookingStatus.CANCELLED, actor, user, note=reason or f"Cancelled by {actor.value.lower()}")
    assignment.cancel_open_assignments(db, booking)
    payments.cancel_payment(booking)
    if actor != Actor.CUSTOMER:
        notify(db, booking.customer.user_id, "BOOKING_CANCELLED", booking)


PROGRESS_NOTIFICATIONS = {
    BookingStatus.PROVIDER_EN_ROUTE: "PROVIDER_EN_ROUTE",
    BookingStatus.PROVIDER_ARRIVED: "PROVIDER_ARRIVED",
    BookingStatus.SERVICE_IN_PROGRESS: "SERVICE_STARTED",
    BookingStatus.COMPLETED_BY_PROVIDER: "SERVICE_COMPLETED",
}


def provider_advance(
    db: Session, provider: Provider, booking: Booking, expected: BookingStatus | None
) -> BookingStatus:
    if booking.provider_id != provider.id:
        raise NotFoundError("Booking not found.")
    target = PROVIDER_PROGRESS.get(booking.status)
    if target is None:
        raise ConflictError("There is no next step for this job.", code="INVALID_STATUS_TRANSITION")
    if expected and expected != target:
        # Guards against double taps / stale screens sending an outdated action.
        raise ConflictError("This job has already moved on. Refresh to see its status.", code="STALE_STATUS")
    transition(db, booking, target, Actor.PROVIDER, provider.user)
    notify(db, booking.customer.user_id, PROGRESS_NOTIFICATIONS[target], booking)
    return target


def customer_confirm_completion(db: Session, booking: Booking, user: User) -> None:
    actor = Actor.ADMIN if user.role_code == RoleCode.ADMIN else Actor.CUSTOMER
    transition(db, booking, BookingStatus.CUSTOMER_CONFIRMED, actor, user)
    if booking.provider:
        notify(db, booking.provider.user_id, "CUSTOMER_CONFIRMED", booking)
    payments.try_close(db, booking)


def get_customer_booking(db: Session, customer: Customer, booking_id) -> Booking:
    booking = db.get(Booking, booking_id)
    # Same response for "missing" and "not yours" so IDs can't be probed.
    if booking is None or booking.customer_id != customer.id:
        raise NotFoundError("Booking not found.")
    return booking


def get_booking(db: Session, booking_id) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise NotFoundError("Booking not found.")
    return booking
