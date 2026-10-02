"""Provider profile, capabilities, verification and earnings."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ValidationFailedError
from app.core.logging import get_logger
from app.models import (
    Booking,
    Provider,
    ProviderAssignment,
    ProviderAvailability,
    ProviderService,
    ProviderServiceArea,
    ProviderSettlement,
    ProviderVerification,
    Service,
    ServiceArea,
    User,
)
from app.models.enums import (
    ACTIVE_ASSIGNED_STATUSES,
    AssignmentStatus,
    BookingStatus,
    SettlementStatus,
    VerificationDecision,
    VerificationStatus,
)
from app.schemas.catalog import AreaOut
from app.schemas.provider import (
    AvailabilityDay,
    EarningRow,
    EarningsOut,
    ProviderDashboard,
    ProviderProfile,
    ServiceBrief,
    VerificationEvent,
)
from app.services import audit
from app.services.notifications import notify
from app.utils.clock import utcnow

log = get_logger("providers")

DONE_STATUSES = (BookingStatus.COMPLETED_BY_PROVIDER, BookingStatus.CUSTOMER_CONFIRMED, BookingStatus.CLOSED)


def set_services(db: Session, provider: Provider, service_ids: list[uuid.UUID]) -> None:
    ids = set(service_ids)
    if ids:
        found = set(db.scalars(select(Service.id).where(Service.id.in_(ids), Service.is_active.is_(True))))
        if found != ids:
            raise ValidationFailedError("One or more selected services are not available.", code="INVALID_SERVICE")
    provider.services = [ps for ps in provider.services if ps.service_id in ids]
    existing = {ps.service_id for ps in provider.services}
    provider.services.extend(ProviderService(provider_id=provider.id, service_id=sid) for sid in ids - existing)


def set_areas(db: Session, provider: Provider, area_ids: list[uuid.UUID]) -> None:
    ids = set(area_ids)
    if ids:
        found = set(db.scalars(select(ServiceArea.id).where(ServiceArea.id.in_(ids), ServiceArea.is_active.is_(True))))
        if found != ids:
            raise ValidationFailedError("One or more selected areas are not available.", code="INVALID_AREA")
    provider.areas = [pa for pa in provider.areas if pa.area_id in ids]
    existing = {pa.area_id for pa in provider.areas}
    provider.areas.extend(ProviderServiceArea(provider_id=provider.id, area_id=aid) for aid in ids - existing)


def set_availability(db: Session, provider: Provider, days: list[AvailabilityDay]) -> None:
    seen = set()
    for d in days:
        if d.day_of_week in seen:
            raise ValidationFailedError("Each day can only appear once.", code="DUPLICATE_DAY")
        seen.add(d.day_of_week)
    provider.availability.clear()
    db.flush()
    provider.availability.extend(
        ProviderAvailability(
            provider_id=provider.id, day_of_week=d.day_of_week, start_time=d.start_time, end_time=d.end_time
        )
        for d in sorted(days, key=lambda d: d.day_of_week)
    )


def missing_setup(provider: Provider) -> list[str]:
    missing = []
    if not provider.services:
        missing.append("SERVICES")
    if not provider.areas:
        missing.append("AREAS")
    if not provider.availability:
        missing.append("AVAILABILITY")
    return missing


def profile_out(provider: Provider) -> ProviderProfile:
    u = provider.user
    return ProviderProfile(
        id=provider.id,
        user_id=u.id,
        provider_type=provider.provider_type,
        display_name=provider.display_name,
        contact_person=provider.contact_person,
        full_name=u.full_name,
        phone=u.phone,
        email=u.email,
        bio=provider.bio,
        years_experience=provider.years_experience,
        registration_number=provider.registration_number,
        verification_status=provider.verification_status,
        verified_at=provider.verified_at,
        is_accepting_jobs=provider.is_accepting_jobs,
        capacity=provider.capacity,
        rating_average=provider.rating_average,
        rating_count=provider.rating_count,
        is_active=u.is_active,
        services=[
            ServiceBrief(id=s.service.id, slug=s.service.slug, name_en=s.service.name_en, name_sw=s.service.name_sw)
            for s in sorted(provider.services, key=lambda s: s.service.display_order)
        ],
        areas=[AreaOut.model_validate(a.area) for a in sorted(provider.areas, key=lambda a: a.area.name)],
        availability=[AvailabilityDay.model_validate(a) for a in provider.availability],
        verification_history=[VerificationEvent.model_validate(v) for v in provider.verifications],
        created_at=provider.created_at,
    )


def completed_jobs_count(db: Session, provider_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count(Booking.id)).where(Booking.provider_id == provider_id, Booking.status.in_(DONE_STATUSES))
        )
        or 0
    )


def dashboard(db: Session, provider: Provider) -> ProviderDashboard:
    open_offers = db.scalar(
        select(func.count(ProviderAssignment.id)).where(
            ProviderAssignment.provider_id == provider.id,
            ProviderAssignment.status == AssignmentStatus.OFFERED,
            ProviderAssignment.expires_at > utcnow(),
        )
    )
    active = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.provider_id == provider.id, Booking.status.in_(ACTIVE_ASSIGNED_STATUSES)
        )
    )
    earnings = earnings_totals(db, provider)
    missing = missing_setup(provider)
    return ProviderDashboard(
        verification_status=provider.verification_status,
        is_accepting_jobs=provider.is_accepting_jobs,
        open_offers=open_offers or 0,
        active_jobs=active or 0,
        completed_jobs=completed_jobs_count(db, provider.id),
        rating_average=provider.rating_average,
        rating_count=provider.rating_count,
        earnings_total=earnings.total_earned,
        earnings_pending=earnings.pending_settlement,
        currency=earnings.currency,
        setup_complete=not missing,
        missing_setup=missing,
    )


EARNING_STATUSES = DONE_STATUSES + (BookingStatus.DISPUTED,)


def earnings_totals(db: Session, provider: Provider) -> EarningsOut:
    """Lifetime totals computed by PostgreSQL (two aggregate queries), without row detail."""
    by_status = dict(
        db.execute(
            select(ProviderSettlement.status, func.coalesce(func.sum(ProviderSettlement.provider_earning), 0))
            .where(ProviderSettlement.provider_id == provider.id)
            .group_by(ProviderSettlement.status)
        ).all()
    )
    awaiting = db.scalar(
        select(func.coalesce(func.sum(Booking.provider_earning), 0)).where(
            Booking.provider_id == provider.id,
            Booking.status.in_(EARNING_STATUSES),
            ~select(ProviderSettlement.id).where(ProviderSettlement.booking_id == Booking.id).exists(),
        )
    )
    pending = Decimal(by_status.get(SettlementStatus.PENDING, 0))
    settled = Decimal(by_status.get(SettlementStatus.SETTLED, 0))
    return EarningsOut(
        currency=get_settings().default_currency,
        total_earned=pending + settled,
        pending_settlement=pending,
        settled=settled,
        awaiting_completion=Decimal(awaiting),
        rows=[],
    )


def earnings_for(db: Session, provider: Provider, limit: int = 100) -> EarningsOut:
    """Totals over all time plus the ``limit`` most recent earning rows."""
    out = earnings_totals(db, provider)
    bookings = (
        db.scalars(
            select(Booking)
            .where(Booking.provider_id == provider.id, Booking.status.in_(EARNING_STATUSES))
            .order_by(Booking.scheduled_date.desc(), Booking.scheduled_start_time.desc())
            .limit(limit)
        )
        .unique()
        .all()
    )
    settlements = {
        s.booking_id: s
        for s in db.scalars(
            select(ProviderSettlement).where(ProviderSettlement.booking_id.in_([b.id for b in bookings]))
        ).unique()
    }
    rows: list[EarningRow] = []
    for b in bookings:
        s = settlements.get(b.id)
        rows.append(
            EarningRow(
                booking_id=b.id,
                reference=b.reference,
                service_name=b.service_name_snapshot,
                scheduled_date=b.scheduled_date.isoformat(),
                status=b.status.value,
                total_amount=b.total_amount,
                commission_amount=b.commission_amount,
                provider_earning=b.provider_earning,
                payment_status=b.payment.status.value if b.payment else None,
                settlement_status=s.status if s else None,
                settled_at=s.settled_at if s else None,
                settlement_reference=s.reference if s else None,
            )
        )
    out.rows = rows
    return out


VERIFICATION_RULES: dict[str, tuple[set[VerificationStatus], VerificationStatus, VerificationDecision, str]] = {
    "APPROVE": (
        {VerificationStatus.PENDING, VerificationStatus.REJECTED},
        VerificationStatus.VERIFIED,
        VerificationDecision.APPROVED,
        "ADMIN_APPROVED_PROVIDER",
    ),
    "REJECT": (
        {VerificationStatus.PENDING},
        VerificationStatus.REJECTED,
        VerificationDecision.REJECTED,
        "ADMIN_REJECTED_PROVIDER",
    ),
    "SUSPEND": (
        {VerificationStatus.VERIFIED},
        VerificationStatus.SUSPENDED,
        VerificationDecision.SUSPENDED,
        "ADMIN_SUSPENDED_PROVIDER",
    ),
    "REACTIVATE": (
        {VerificationStatus.SUSPENDED},
        VerificationStatus.VERIFIED,
        VerificationDecision.REACTIVATED,
        "ADMIN_REACTIVATED_PROVIDER",
    ),
}
NOTIFY_ON = {
    "APPROVE": "PROVIDER_VERIFIED",
    "REACTIVATE": "PROVIDER_VERIFIED",
    "REJECT": "PROVIDER_REJECTED",
    "SUSPEND": "PROVIDER_SUSPENDED",
}


def apply_verification(db: Session, admin: User, provider: Provider, action: str, notes: str | None) -> None:
    allowed_from, new_status, decision, audit_action = VERIFICATION_RULES[action]
    if provider.verification_status not in allowed_from:
        raise ConflictError(
            f"Cannot {action.lower()} a provider who is {provider.verification_status.value.lower()}.",
            code="INVALID_VERIFICATION_ACTION",
        )
    if action == "APPROVE" and missing_setup(provider):
        raise ValidationFailedError(
            "Provider must have services, areas and availability before approval.", code="PROVIDER_SETUP_INCOMPLETE"
        )
    if action == "SUSPEND":
        active = db.scalar(
            select(func.count(Booking.id)).where(
                Booking.provider_id == provider.id, Booking.status.in_(ACTIVE_ASSIGNED_STATUSES)
            )
        )
        if active:
            raise ConflictError(
                "Reassign this provider's active jobs before suspending.", code="PROVIDER_HAS_ACTIVE_JOBS"
            )
    old = provider.verification_status
    provider.verification_status = new_status
    if new_status == VerificationStatus.VERIFIED and provider.verified_at is None:
        provider.verified_at = utcnow()
    db.add(
        ProviderVerification(
            provider_id=provider.id, decision=decision, notes=notes, reviewed_by_id=admin.id, created_at=utcnow()
        )
    )
    notify(db, provider.user_id, NOTIFY_ON[action])
    audit.record(
        db,
        admin,
        audit_action,
        "provider",
        provider.id,
        {"name": provider.display_name, "from": old, "to": new_status, "notes": notes},
    )
    log.info("provider.verification", extra={"provider": str(provider.id), "action": action})


def recalculate_rating(db: Session, provider: Provider) -> None:
    from app.models import Review

    avg, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.provider_id == provider.id, Review.is_hidden.is_(False)
        )
    ).one()
    provider.rating_count = count or 0
    provider.rating_average = Decimal(avg).quantize(Decimal("0.01")) if avg else Decimal(0)
