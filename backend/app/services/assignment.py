"""Provider assignment engine.

Eligibility (all must hold):
  1. provider's user account is active
  2. provider is VERIFIED and accepting jobs
  3. provider offers the requested service
  4. provider covers the booking's service area
  5. provider's weekly hours cover the whole job window
  6. provider has free capacity — overlapping assigned jobs and open offers < capacity

Ranking is deterministic: higher effective rating first (unrated providers get a
neutral score so new providers still receive work), then fewer jobs that day,
then longest-registered. Swap :func:`rank_key` to evolve the strategy.

Concurrency: callers hold the booking row lock (see :mod:`app.services.locks`); this
module additionally locks the provider row before consuming capacity. The database
enforces "one open assignment per booking" with a partial unique index.
"""

import uuid
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal

from sqlalchemy import and_, exists, select, true
from sqlalchemy.orm import Session

from app.core import events
from app.core.errors import ConflictError, NotFoundError, ProviderUnavailableError, ValidationFailedError
from app.core.logging import get_logger
from app.models import (
    Booking,
    Provider,
    ProviderAssignment,
    ProviderAvailability,
    ProviderService,
    ProviderServiceArea,
    User,
)
from app.models.enums import ACTIVE_ASSIGNED_STATUSES, AssignmentStatus, BookingStatus, VerificationStatus
from app.services import audit, platform_settings
from app.services.lifecycle import Actor, transition
from app.services.locks import lock_booking, lock_provider
from app.services.notifications import notify, notify_admins
from app.utils.clock import add_minutes, expires_in, overlaps, utcnow

log = get_logger("assignment")

NEUTRAL_RATING = Decimal("4.00")
OPEN_ASSIGNMENT_STATUSES = (AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED)


@dataclass(frozen=True)
class JobSpec:
    service_id: uuid.UUID
    area_id: uuid.UUID
    day: date
    start: time
    duration_minutes: int
    booking_id: uuid.UUID | None = None

    @classmethod
    def of(cls, booking: Booking) -> "JobSpec":
        return cls(
            booking.service_id,
            booking.area_id,
            booking.scheduled_date,
            booking.scheduled_start_time,
            booking.estimated_duration_minutes,
            booking.id,
        )


@dataclass(frozen=True)
class Candidate:
    provider: Provider
    jobs_that_day: int

    @property
    def effective_rating(self) -> Decimal:
        return self.provider.rating_average if self.provider.rating_count else NEUTRAL_RATING


def rank_key(c: Candidate) -> tuple:
    return (-c.effective_rating, c.jobs_that_day, c.provider.created_at, str(c.provider.id))


def commitments_for_day(
    db: Session,
    provider_ids: list[uuid.UUID],
    day: date,
    *,
    exclude_booking: uuid.UUID | None = None,
    include_offers: bool = True,
) -> dict[uuid.UUID, list[tuple[time, int]]]:
    """Jobs each provider already holds on ``day``: assigned bookings and (optionally) live offers.

    Live offers count when *matching* (an offered slot is reserved while the provider
    decides) but not when the provider *accepts*: holding two overlapping offers must not
    stop them from accepting one of them.
    """
    result: dict[uuid.UUID, list[tuple[time, int]]] = {pid: [] for pid in provider_ids}
    if not provider_ids:
        return result
    not_this = Booking.id != exclude_booking if exclude_booking else true()
    rows = list(
        db.execute(
            select(Booking.provider_id, Booking.scheduled_start_time, Booking.estimated_duration_minutes).where(
                Booking.provider_id.in_(provider_ids),
                Booking.scheduled_date == day,
                Booking.status.in_(ACTIVE_ASSIGNED_STATUSES),
                not_this,
            )
        ).all()
    )
    if include_offers:
        rows += db.execute(
            select(ProviderAssignment.provider_id, Booking.scheduled_start_time, Booking.estimated_duration_minutes)
            .join(Booking, Booking.id == ProviderAssignment.booking_id)
            .where(
                ProviderAssignment.provider_id.in_(provider_ids),
                ProviderAssignment.status == AssignmentStatus.OFFERED,
                ProviderAssignment.expires_at > utcnow(),
                Booking.scheduled_date == day,
                not_this,
            )
        ).all()
    for pid, start, minutes in rows:
        result[pid].append((start, minutes))
    return result


def _commitments(
    db: Session, provider_ids: list[uuid.UUID], spec: JobSpec, *, include_offers: bool = True
) -> dict[uuid.UUID, list[tuple[time, int]]]:
    return commitments_for_day(
        db, provider_ids, spec.day, exclude_booking=spec.booking_id, include_offers=include_offers
    )


def fits(capacity: int, commitments: list[tuple[time, int]], start: time, duration_minutes: int) -> bool:
    clashes = sum(1 for s, minutes in commitments if overlaps(s, minutes, start, duration_minutes))
    return clashes < capacity


def has_capacity(provider: Provider, commitments: list[tuple[time, int]], spec: JobSpec) -> bool:
    return fits(provider.capacity, commitments, spec.start, spec.duration_minutes)


def eligible_base_query(service_id: uuid.UUID, area_id: uuid.UUID):
    """Providers who may do this service in this area (ignores hours and capacity)."""
    return (
        select(Provider)
        .join(User, User.id == Provider.user_id)
        .where(
            User.is_active.is_(True),
            Provider.verification_status == VerificationStatus.VERIFIED,
            Provider.is_accepting_jobs.is_(True),
            exists().where(and_(ProviderService.provider_id == Provider.id, ProviderService.service_id == service_id)),
            exists().where(
                and_(ProviderServiceArea.provider_id == Provider.id, ProviderServiceArea.area_id == area_id)
            ),
        )
    )


def find_eligible(
    db: Session, spec: JobSpec, exclude: set[uuid.UUID] | None = None, check_hours: bool = True
) -> list[Candidate]:
    end = add_minutes(spec.start, spec.duration_minutes)
    stmt = eligible_base_query(spec.service_id, spec.area_id)
    if check_hours:
        stmt = stmt.where(
            exists().where(
                and_(
                    ProviderAvailability.provider_id == Provider.id,
                    ProviderAvailability.day_of_week == spec.day.isoweekday(),
                    ProviderAvailability.start_time <= spec.start,
                    ProviderAvailability.end_time >= end,
                )
            )
        )
    if exclude:
        stmt = stmt.where(Provider.id.not_in(exclude))
    providers = list(db.scalars(stmt).unique())
    commitments = _commitments(db, [p.id for p in providers], spec)
    candidates = [Candidate(p, len(commitments[p.id])) for p in providers if has_capacity(p, commitments[p.id], spec)]
    return sorted(candidates, key=rank_key)


def _offer_notification(db: Session, booking: Booking, provider: Provider, type_: str = "JOB_OFFERED") -> None:
    notify(
        db,
        provider.user_id,
        type_,
        booking,
        service=booking.service_name_snapshot,
        area=booking.area.name,
        when=f"{booking.scheduled_date:%d %b} {booking.scheduled_start_time:%H:%M}",
    )


def _offer(
    db: Session, booking: Booking, provider: Provider, *, manual: bool = False, by: User | None = None
) -> ProviderAssignment:
    ttl = platform_settings.offer_ttl_minutes(db)
    assignment = ProviderAssignment(
        booking_id=booking.id,
        provider_id=provider.id,
        status=AssignmentStatus.OFFERED,
        is_manual=manual,
        assigned_by_id=by.id if by else None,
        offered_at=utcnow(),
        expires_at=expires_in(ttl),
    )
    db.add(assignment)
    _offer_notification(db, booking, provider)
    events.publish(db, events.ASSIGNMENT_OFFERED, booking=booking.reference, provider_id=str(provider.id))
    log.info("assignment.offered", extra={"booking": booking.reference, "provider": str(provider.id), "manual": manual})
    return assignment


def _tried_provider_ids(db: Session, booking: Booking) -> set[uuid.UUID]:
    return set(db.scalars(select(ProviderAssignment.provider_id).where(ProviderAssignment.booking_id == booking.id)))


def dispatch(db: Session, booking: Booking) -> ProviderAssignment | None:
    """Offer the booking to the best eligible provider not yet tried, or escalate to admins.

    The caller holds the booking lock. Each candidate's row is locked with SKIP LOCKED and
    its capacity re-checked under that lock, so two bookings dispatched at the same moment
    cannot both reserve the last free slot of the same provider.
    """
    db.flush()
    spec = JobSpec.of(booking)
    for candidate in find_eligible(db, spec, exclude=_tried_provider_ids(db, booking)):
        provider = lock_provider(db, candidate.provider.id, skip_locked=True)
        if provider is None:  # busy in another transaction right now: try the next best
            continue
        if not has_capacity(provider, _commitments(db, [provider.id], spec)[provider.id], spec):
            continue
        if booking.status != BookingStatus.FINDING_PROVIDER:
            transition(db, booking, BookingStatus.FINDING_PROVIDER, Actor.SYSTEM)
        return _offer(db, booking, provider)
    if booking.status != BookingStatus.REASSIGNMENT_REQUIRED:
        transition(
            db, booking, BookingStatus.REASSIGNMENT_REQUIRED, Actor.SYSTEM, note="No eligible provider available"
        )
        notify_admins(db, "ADMIN_REASSIGNMENT_REQUIRED", booking)
        notify(db, booking.customer.user_id, "BOOKING_DELAYED", booking)
    events.publish(db, events.ASSIGNMENT_UNMATCHED, booking=booking.reference)
    log.warning("assignment.no_candidate", extra={"booking": booking.reference})
    return None


def _provider_assignment(db: Session, provider: Provider, assignment_id: uuid.UUID) -> ProviderAssignment:
    assignment = db.get(ProviderAssignment, assignment_id)
    if assignment is None or assignment.provider_id != provider.id:
        raise NotFoundError("Job not found.")
    return assignment


def accept_offer(db: Session, provider: Provider, assignment_id: uuid.UUID) -> ProviderAssignment:
    assignment = _provider_assignment(db, provider, assignment_id)
    booking = lock_booking(db, assignment.booking_id)
    db.refresh(assignment)  # fresh state now that the booking (and its assignments) are ours
    if assignment.status == AssignmentStatus.ACCEPTED and booking.provider_id == provider.id:
        return assignment  # double tap / network retry: already done, same result
    if assignment.status != AssignmentStatus.OFFERED:
        raise ConflictError("This job offer is no longer available.", code="OFFER_NOT_AVAILABLE")
    if assignment.expires_at and assignment.expires_at <= utcnow():
        raise ConflictError("This job offer has expired.", code="OFFER_EXPIRED")

    # Serialise this provider's acceptances: a concurrent accept of an overlapping job waits
    # here and then sees this one in its capacity check.
    provider = lock_provider(db, provider.id)
    if provider.verification_status != VerificationStatus.VERIFIED or not provider.user.is_active:
        raise ProviderUnavailableError("Your account must be verified and active to accept jobs.")
    spec = JobSpec.of(booking)
    if not has_capacity(provider, _commitments(db, [provider.id], spec, include_offers=False)[provider.id], spec):
        raise ProviderUnavailableError("You already have a job at this time.", code="SCHEDULE_CONFLICT")

    assignment.status = AssignmentStatus.ACCEPTED
    assignment.responded_at = utcnow()
    booking.provider_id = provider.id
    transition(db, booking, BookingStatus.PROVIDER_ASSIGNED, Actor.PROVIDER, provider.user)
    notify(db, booking.customer.user_id, "PROVIDER_ASSIGNED", booking, provider=provider.display_name)
    events.publish(
        db,
        events.ASSIGNMENT_ACCEPTED,
        booking=booking.reference,
        provider_id=str(provider.id),
        wait_seconds=(assignment.responded_at - assignment.offered_at).total_seconds(),
    )
    log.info("assignment.accepted", extra={"booking": booking.reference, "provider": str(provider.id)})
    return assignment


def reject_offer(db: Session, provider: Provider, assignment_id: uuid.UUID, reason: str | None) -> ProviderAssignment:
    assignment = _provider_assignment(db, provider, assignment_id)
    booking = lock_booking(db, assignment.booking_id)
    db.refresh(assignment)
    if assignment.status == AssignmentStatus.REJECTED:
        return assignment  # repeated tap
    if assignment.status != AssignmentStatus.OFFERED:
        raise ConflictError("This job offer is no longer available.", code="OFFER_NOT_AVAILABLE")
    assignment.status = AssignmentStatus.REJECTED
    assignment.responded_at = utcnow()
    assignment.response_note = reason
    events.publish(db, events.ASSIGNMENT_REJECTED, booking=booking.reference, provider_id=str(provider.id))
    log.info("assignment.rejected", extra={"booking": booking.reference, "provider": str(provider.id)})
    if booking.status in (BookingStatus.FINDING_PROVIDER, BookingStatus.REASSIGNMENT_REQUIRED):
        db.flush()  # the rejected offer must be closed before the next one is opened
        dispatch(db, booking)
    return assignment


def withdraw(db: Session, provider: Provider, booking: Booking, reason: str | None) -> None:
    """Provider hands back an accepted job before travelling. The booking is re-dispatched.

    The caller holds the booking lock.
    """
    if booking.provider_id != provider.id or booking.status != BookingStatus.PROVIDER_ASSIGNED:
        raise ConflictError("You can only release a job before you set off.", code="CANNOT_WITHDRAW")
    close_open_assignments(db, booking, AssignmentStatus.WITHDRAWN, reason)
    booking.provider_id = None
    transition(
        db, booking, BookingStatus.FINDING_PROVIDER, Actor.PROVIDER, provider.user, note=reason or "Provider withdrew"
    )
    db.flush()
    dispatch(db, booking)


def close_open_assignments(
    db: Session, booking: Booking, status: AssignmentStatus, note: str | None = None, notify_type: str | None = None
) -> None:
    open_assignments = db.scalars(
        select(ProviderAssignment)
        .where(ProviderAssignment.booking_id == booking.id, ProviderAssignment.status.in_(OPEN_ASSIGNMENT_STATUSES))
        .execution_options(populate_existing=True)
    ).all()
    for a in open_assignments:
        a.status = status
        a.responded_at = a.responded_at or utcnow()
        a.response_note = note
        if notify_type:
            notify(db, a.provider.user_id, notify_type, booking)


def cancel_open_assignments(db: Session, booking: Booking) -> None:
    close_open_assignments(db, booking, AssignmentStatus.CANCELLED, "Booking cancelled", notify_type="JOB_CANCELLED")


def due_offers(db: Session, limit: int = 100) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """(assignment id, booking id) of offers past their deadline, oldest first."""
    return [
        (aid, bid)
        for aid, bid in db.execute(
            select(ProviderAssignment.id, ProviderAssignment.booking_id)
            .where(ProviderAssignment.status == AssignmentStatus.OFFERED, ProviderAssignment.expires_at <= utcnow())
            .order_by(ProviderAssignment.expires_at)
            .limit(limit)
        ).all()
    ]


def expire_offer(db: Session, assignment_id: uuid.UUID, booking_id: uuid.UUID) -> bool:
    """Expire one stale offer and re-dispatch its booking. Returns False if skipped.

    A booking that another transaction is working on right now (e.g. the provider is
    accepting at the last second) is skipped with SKIP LOCKED and retried next pass,
    so the job never blocks or deadlocks against user requests. Safe with any number
    of workers.
    """
    booking = lock_booking(db, booking_id, skip_locked=True)
    if booking is None:
        return False
    assignment = db.get(ProviderAssignment, assignment_id, populate_existing=True)
    if assignment is None or assignment.status != AssignmentStatus.OFFERED or assignment.expires_at > utcnow():
        return False
    assignment.status = AssignmentStatus.EXPIRED
    assignment.responded_at = utcnow()
    notify(db, assignment.provider.user_id, "JOB_OFFER_EXPIRED", booking)
    events.publish(db, events.ASSIGNMENT_EXPIRED, booking=booking.reference, provider_id=str(assignment.provider_id))
    log.info("assignment.expired", extra={"booking": booking.reference, "provider": str(assignment.provider_id)})
    if booking.status == BookingStatus.FINDING_PROVIDER:
        db.flush()
        dispatch(db, booking)
    return True


MANUAL_ASSIGNABLE = {
    BookingStatus.CONFIRMED,
    BookingStatus.FINDING_PROVIDER,
    BookingStatus.REASSIGNMENT_REQUIRED,
    BookingStatus.PROVIDER_ASSIGNED,
    BookingStatus.PROVIDER_EN_ROUTE,
}


def manual_assign(
    db: Session, admin: User, booking: Booking, provider_id: uuid.UUID, direct: bool, note: str | None
) -> ProviderAssignment:
    booking = lock_booking(db, booking.id)
    if booking.status not in MANUAL_ASSIGNABLE:
        raise ConflictError("This booking cannot be (re)assigned in its current status.", code="NOT_ASSIGNABLE")
    provider = lock_provider(db, provider_id)
    if provider is None:
        raise NotFoundError("Provider not found.")
    if provider.verification_status != VerificationStatus.VERIFIED or not provider.user.is_active:
        raise ProviderUnavailableError("Only verified, active providers can be assigned.")
    if not any(s.service_id == booking.service_id for s in provider.services):
        raise ValidationFailedError("This provider does not offer the requested service.", code="SERVICE_NOT_OFFERED")
    spec = JobSpec.of(booking)
    # A direct assignment consumes real capacity; an offer also respects slots held by other offers.
    if not has_capacity(provider, _commitments(db, [provider.id], spec, include_offers=not direct)[provider.id], spec):
        raise ProviderUnavailableError("This provider already has a job at this time.", code="SCHEDULE_CONFLICT")

    previous_provider = booking.provider_id
    close_open_assignments(db, booking, AssignmentStatus.CANCELLED, "Reassigned by admin", notify_type="JOB_CANCELLED")
    db.flush()  # close the old open assignment before the new one exists (one-open-per-booking index)
    assignment = ProviderAssignment(
        booking_id=booking.id,
        provider_id=provider.id,
        is_manual=True,
        assigned_by_id=admin.id,
        offered_at=utcnow(),
        response_note=note,
    )
    if direct:
        assignment.status = AssignmentStatus.ACCEPTED
        assignment.responded_at = utcnow()
        db.add(assignment)
        booking.provider_id = provider.id
        transition(db, booking, BookingStatus.PROVIDER_ASSIGNED, Actor.ADMIN, admin, note=note or "Assigned by admin")
        notify(db, provider.user_id, "JOB_ASSIGNED", booking)
        notify(db, booking.customer.user_id, "PROVIDER_ASSIGNED", booking, provider=provider.display_name)
        events.publish(db, events.ASSIGNMENT_ACCEPTED, booking=booking.reference, provider_id=str(provider.id))
    else:
        booking.provider_id = None
        if booking.status != BookingStatus.FINDING_PROVIDER:
            transition(db, booking, BookingStatus.FINDING_PROVIDER, Actor.ADMIN, admin, note=note or "Offered by admin")
        assignment.status = AssignmentStatus.OFFERED
        assignment.expires_at = expires_in(platform_settings.offer_ttl_minutes(db))
        db.add(assignment)
        _offer_notification(db, booking, provider)
        events.publish(db, events.ASSIGNMENT_OFFERED, booking=booking.reference, provider_id=str(provider.id))
    audit.record(
        db,
        admin,
        "ADMIN_REASSIGNED_BOOKING" if previous_provider else "ADMIN_ASSIGNED_BOOKING",
        "booking",
        booking.id,
        {
            "reference": booking.reference,
            "provider_id": str(provider.id),
            "previous_provider_id": str(previous_provider) if previous_provider else None,
            "direct": direct,
        },
    )
    return assignment
