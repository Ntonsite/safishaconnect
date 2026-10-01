"""Admin operations that need side effects beyond a plain status change."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import PaymentStateError
from app.models import Booking, Complaint, Customer, Payment, Provider, ProviderSettlement, User
from app.models.enums import (
    AssignmentStatus,
    BookingStatus,
    ComplaintStatus,
    PaymentMethod,
    PaymentStatus,
    SettlementStatus,
    VerificationStatus,
)
from app.schemas.admin import StatsOut
from app.services import assignment, audit, bookings, payments
from app.services.lifecycle import Actor, transition
from app.services.notifications import notify
from app.utils.clock import local_today

S = BookingStatus


def admin_set_status(db: Session, admin: User, booking: Booking, target: S, note: str | None) -> None:
    old = booking.status
    if target == S.CANCELLED:
        bookings.cancel_booking(db, booking, admin, Actor.ADMIN, note)
    elif target == S.CONFIRMED:
        bookings.confirm_booking(db, booking, admin, Actor.ADMIN)
    elif target == S.CUSTOMER_CONFIRMED:
        bookings.customer_confirm_completion(db, booking, admin)
    elif target == S.CLOSED:
        if booking.status == S.CUSTOMER_CONFIRMED and booking.payment.status != PaymentStatus.PAID:
            raise PaymentStateError("Confirm the payment before closing this booking.", code="PAYMENT_NOT_PAID")
        transition(db, booking, S.CLOSED, Actor.ADMIN, admin, note=note)
        payments.ensure_settlement(db, booking)
        notify(db, booking.customer.user_id, "BOOKING_CLOSED", booking)
    elif target in (S.FINDING_PROVIDER, S.REASSIGNMENT_REQUIRED):
        assignment.close_open_assignments(
            db, booking, AssignmentStatus.CANCELLED, "Reassignment by admin", notify_type="JOB_CANCELLED"
        )
        booking.provider_id = None
        transition(db, booking, target, Actor.ADMIN, admin, note=note)
        if target == S.FINDING_PROVIDER:
            assignment.dispatch(db, booking)
    else:
        transition(db, booking, target, Actor.ADMIN, admin, note=note)
        if target in bookings.PROGRESS_NOTIFICATIONS:
            notify(db, booking.customer.user_id, bookings.PROGRESS_NOTIFICATIONS[target], booking)
    audit.record(
        db,
        admin,
        "ADMIN_CHANGED_BOOKING_STATUS",
        "booking",
        booking.id,
        {"reference": booking.reference, "from": old, "to": target, "note": note},
    )


def _count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def stats(db: Session) -> StatsOut:
    completed = (S.COMPLETED_BY_PROVIDER, S.CUSTOMER_CONFIRMED, S.CLOSED)
    by_status = dict(db.execute(select(Booking.status, func.count(Booking.id)).group_by(Booking.status)).all())
    # GBV counts every booking not cancelled; commission is only recognised once a booking is closed.
    gross = db.scalar(
        select(func.coalesce(func.sum(Booking.total_amount), 0)).where(
            Booking.status.not_in((S.CANCELLED, S.PENDING_CONFIRMATION))
        )
    )
    commission = db.scalar(
        select(func.coalesce(func.sum(Booking.commission_amount), 0)).where(Booking.status == S.CLOSED)
    )
    return StatsOut(
        currency=get_settings().default_currency,
        total_customers=_count(db, select(func.count(Customer.id))),
        active_providers=_count(
            db,
            select(func.count(Provider.id))
            .join(User, User.id == Provider.user_id)
            .where(Provider.verification_status == VerificationStatus.VERIFIED, User.is_active.is_(True)),
        ),
        providers_awaiting_verification=_count(
            db, select(func.count(Provider.id)).where(Provider.verification_status == VerificationStatus.PENDING)
        ),
        total_bookings=sum(by_status.values()),
        todays_bookings=_count(db, select(func.count(Booking.id)).where(Booking.scheduled_date == local_today())),
        completed_bookings=sum(by_status.get(s, 0) for s in completed),
        cancelled_bookings=by_status.get(S.CANCELLED, 0),
        gross_booking_value=Decimal(gross),
        platform_commission=Decimal(commission),
        pending_assignments=by_status.get(S.FINDING_PROVIDER, 0) + by_status.get(S.REASSIGNMENT_REQUIRED, 0),
        open_complaints=_count(
            db,
            select(func.count(Complaint.id)).where(
                Complaint.status.in_((ComplaintStatus.OPEN, ComplaintStatus.IN_REVIEW))
            ),
        ),
        cash_awaiting_confirmation=_count(
            db,
            select(func.count(Payment.id))
            .join(Booking, Booking.id == Payment.booking_id)
            .where(
                Payment.method == PaymentMethod.CASH,
                Payment.status == PaymentStatus.PENDING,
                Booking.status.in_((S.COMPLETED_BY_PROVIDER, S.CUSTOMER_CONFIRMED, S.DISPUTED)),
            ),
        ),
        settlements_pending_amount=Decimal(
            db.scalar(
                select(func.coalesce(func.sum(ProviderSettlement.provider_earning), 0)).where(
                    ProviderSettlement.status == SettlementStatus.PENDING
                )
            )
        ),
        bookings_by_status={k.value: v for k, v in by_status.items()},
    )
