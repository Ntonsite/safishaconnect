"""Provider self-service portal. Providers only ever see their own offers and jobs."""

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.models import Booking, ProviderAssignment, Review
from app.models.enums import AssignmentStatus, BookingStatus, RoleCode
from app.schemas.booking import BookingDetail, JobOut, ReasonIn
from app.schemas.feedback import ReviewOut
from app.schemas.provider import (
    AvailabilityUpdate,
    EarningsOut,
    IdList,
    ProviderDashboard,
    ProviderProfile,
    ProviderUpdate,
)
from app.security.deps import CurrentProvider, DbSession
from app.services import assignment, booking_views, feedback, provider_profile
from app.services import bookings as booking_service
from app.utils.clock import utcnow

router = APIRouter(prefix="/providers/me", tags=["providers"])
assignments = APIRouter(prefix="/assignments", tags=["assignments"])

ACTIVE = (
    BookingStatus.PROVIDER_ASSIGNED,
    BookingStatus.PROVIDER_EN_ROUTE,
    BookingStatus.PROVIDER_ARRIVED,
    BookingStatus.SERVICE_IN_PROGRESS,
    BookingStatus.COMPLETED_BY_PROVIDER,
    BookingStatus.DISPUTED,
)
DONE = (BookingStatus.CUSTOMER_CONFIRMED, BookingStatus.CLOSED)


@router.get("", response_model=ProviderProfile)
def my_profile(provider: CurrentProvider) -> ProviderProfile:
    return provider_profile.profile_out(provider)


@router.patch("", response_model=ProviderProfile)
def update_profile(data: ProviderUpdate, provider: CurrentProvider, db: DbSession) -> ProviderProfile:
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(provider, field, value.strip() if isinstance(value, str) else value)
    if provider.provider_type.value == "INDIVIDUAL":
        provider.capacity = 1
    db.commit()
    return provider_profile.profile_out(provider)


@router.put("/services", response_model=ProviderProfile)
def set_services(data: IdList, provider: CurrentProvider, db: DbSession) -> ProviderProfile:
    provider_profile.set_services(db, provider, data.ids)
    db.commit()
    return provider_profile.profile_out(provider)


@router.put("/areas", response_model=ProviderProfile)
def set_areas(data: IdList, provider: CurrentProvider, db: DbSession) -> ProviderProfile:
    provider_profile.set_areas(db, provider, data.ids)
    db.commit()
    return provider_profile.profile_out(provider)


@router.put("/availability", response_model=ProviderProfile)
def set_availability(data: AvailabilityUpdate, provider: CurrentProvider, db: DbSession) -> ProviderProfile:
    provider_profile.set_availability(db, provider, data.days)
    db.commit()
    db.refresh(provider)
    return provider_profile.profile_out(provider)


@router.get("/dashboard", response_model=ProviderDashboard)
def dashboard(provider: CurrentProvider, db: DbSession) -> ProviderDashboard:
    return provider_profile.dashboard(db, provider)


@router.get("/earnings", response_model=EarningsOut)
def earnings(provider: CurrentProvider, db: DbSession) -> EarningsOut:
    return provider_profile.earnings_for(db, provider)


@router.get("/reviews", response_model=list[ReviewOut])
def my_reviews(provider: CurrentProvider, db: DbSession) -> list[ReviewOut]:
    rows = db.scalars(
        select(Review)
        .where(Review.provider_id == provider.id, Review.is_hidden.is_(False))
        .order_by(Review.created_at.desc())
    )
    return [feedback.review_out(r) for r in rows.unique()]


def _job(db, provider, a: ProviderAssignment) -> JobOut:
    return JobOut(
        assignment_id=a.id,
        assignment_status=a.status,
        offered_at=a.offered_at,
        expires_at=a.expires_at,
        responded_at=a.responded_at,
        booking=booking_views.detail(db, a.booking, RoleCode.PROVIDER, provider_id=provider.id, assignment=a),
    )


@router.get("/jobs", response_model=list[JobOut])
def my_jobs(
    provider: CurrentProvider,
    db: DbSession,
    scope: Literal["offers", "active", "completed"] = "active",
) -> list[JobOut]:
    stmt = (
        select(ProviderAssignment)
        .join(Booking, Booking.id == ProviderAssignment.booking_id)
        .where(ProviderAssignment.provider_id == provider.id)
    )
    if scope == "offers":
        stmt = stmt.where(
            ProviderAssignment.status == AssignmentStatus.OFFERED, ProviderAssignment.expires_at > utcnow()
        ).order_by(ProviderAssignment.expires_at)
    else:
        statuses = ACTIVE if scope == "active" else DONE
        stmt = stmt.where(
            ProviderAssignment.status == AssignmentStatus.ACCEPTED,
            Booking.provider_id == provider.id,
            Booking.status.in_(statuses),
        )
        stmt = stmt.order_by(
            Booking.scheduled_date if scope == "active" else Booking.scheduled_date.desc(), Booking.scheduled_start_time
        )
    return [_job(db, provider, a) for a in db.scalars(stmt).unique()]


def _accepted_assignment(db, provider, booking_id: uuid.UUID) -> ProviderAssignment:
    a = db.scalar(
        select(ProviderAssignment)
        .where(
            ProviderAssignment.booking_id == booking_id,
            ProviderAssignment.provider_id == provider.id,
            ProviderAssignment.status.in_((AssignmentStatus.ACCEPTED, AssignmentStatus.OFFERED)),
        )
        .order_by(ProviderAssignment.offered_at.desc())
        .limit(1)
    )
    if a is None:
        raise NotFoundError("Job not found.")
    return a


@router.get("/jobs/{booking_id}", response_model=JobOut)
def job_detail(booking_id: uuid.UUID, provider: CurrentProvider, db: DbSession) -> JobOut:
    return _job(db, provider, _accepted_assignment(db, provider, booking_id))


class AdvanceIn(BaseModel):
    expected_status: BookingStatus | None = Field(
        default=None, description="The status the provider intends to move to; protects against double taps."
    )


@router.post("/jobs/{booking_id}/advance", response_model=JobOut)
def advance_job(booking_id: uuid.UUID, data: AdvanceIn, provider: CurrentProvider, db: DbSession) -> JobOut:
    a = _accepted_assignment(db, provider, booking_id)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update(of=Booking))
    booking_service.provider_advance(db, provider, booking, data.expected_status)
    db.commit()
    return _job(db, provider, a)


@router.post("/jobs/{booking_id}/withdraw", response_model=BookingDetail)
def withdraw_job(booking_id: uuid.UUID, data: ReasonIn, provider: CurrentProvider, db: DbSession) -> BookingDetail:
    _accepted_assignment(db, provider, booking_id)
    booking = booking_service.get_booking(db, booking_id)
    assignment.withdraw(db, provider, booking, data.reason)
    db.commit()
    return booking_views.detail(db, booking, RoleCode.PROVIDER, provider_id=provider.id)


@assignments.post("/{assignment_id}/accept", response_model=JobOut)
def accept(assignment_id: uuid.UUID, provider: CurrentProvider, db: DbSession) -> JobOut:
    a = assignment.accept_offer(db, provider, assignment_id)
    db.commit()
    return _job(db, provider, a)


@assignments.post("/{assignment_id}/reject", response_model=JobOut)
def reject(assignment_id: uuid.UUID, data: ReasonIn, provider: CurrentProvider, db: DbSession) -> JobOut:
    a = assignment.reject_offer(db, provider, assignment_id, data.reason)
    db.commit()
    return _job(db, provider, a)
