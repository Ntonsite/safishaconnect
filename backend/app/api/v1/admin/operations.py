"""Admin: bookings, assignment, payments, settlements, complaints, reviews."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.v1.admin.common import PagingDep, admin_only, paginate
from app.core.errors import NotFoundError
from app.models import Booking, Complaint, Customer, Payment, ProviderSettlement, Review, User
from app.models.enums import BookingStatus, ComplaintStatus, PaymentMethod, PaymentStatus, RoleCode, SettlementStatus
from app.schemas.admin import PaymentRow, PaymentStatusUpdate, SettleIn, SettlementRow
from app.schemas.booking import AdminStatusIn, BookingDetail, BookingSummary, EligibleProviderOut, ManualAssignIn
from app.schemas.common import Page
from app.schemas.feedback import ComplaintOut, ComplaintUpdate, ReviewModerate, ReviewOut
from app.security.deps import AdminUser, DbSession
from app.services import admin_ops, assignment, booking_views, feedback, payments
from app.services import bookings as booking_service

router = APIRouter(dependencies=admin_only)


def _detail(db, booking: Booking) -> BookingDetail:
    return booking_views.detail(db, booking, RoleCode.ADMIN)


@router.get("/bookings", response_model=Page[BookingSummary], tags=["admin: bookings"])
def list_bookings(
    db: DbSession,
    paging: PagingDep,
    status: Annotated[list[BookingStatus] | None, Query()] = None,
    service_id: uuid.UUID | None = None,
    provider_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
) -> Page[BookingSummary]:
    stmt = select(Booking).order_by(Booking.scheduled_date.desc(), Booking.scheduled_start_time.desc())
    if status:
        stmt = stmt.where(Booking.status.in_(status))
    for column, value in (
        (Booking.service_id, service_id),
        (Booking.provider_id, provider_id),
        (Booking.customer_id, customer_id),
        (Booking.area_id, area_id),
    ):
        if value:
            stmt = stmt.where(column == value)
    if date_from:
        stmt = stmt.where(Booking.scheduled_date >= date_from)
    if date_to:
        stmt = stmt.where(Booking.scheduled_date <= date_to)
    if q:
        like = f"%{q.strip()}%"
        stmt = (
            stmt.join(Customer, Customer.id == Booking.customer_id)
            .join(User, User.id == Customer.user_id)
            .where(or_(Booking.reference.ilike(like), User.full_name.ilike(like), User.phone.ilike(like)))
        )
    rows, total = paginate(db, stmt, paging)
    return Page(
        items=[booking_views.summary(b, include_customer=True) for b in rows],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get("/bookings/{booking_id}", response_model=BookingDetail, tags=["admin: bookings"])
def get_booking(booking_id: uuid.UUID, db: DbSession) -> BookingDetail:
    return _detail(db, booking_service.get_booking(db, booking_id))


@router.get(
    "/bookings/{booking_id}/eligible-providers", response_model=list[EligibleProviderOut], tags=["admin: bookings"]
)
def eligible_providers(
    booking_id: uuid.UUID, db: DbSession, include_off_hours: bool = False
) -> list[EligibleProviderOut]:
    booking = booking_service.get_booking(db, booking_id)
    candidates = assignment.find_eligible(db, assignment.JobSpec.of(booking), check_hours=not include_off_hours)
    return [
        EligibleProviderOut(
            id=c.provider.id,
            display_name=c.provider.display_name,
            provider_type=c.provider.provider_type,
            rating_average=c.provider.rating_average,
            rating_count=c.provider.rating_count,
            jobs_that_day=c.jobs_that_day,
        )
        for c in candidates
    ]


@router.post("/bookings/{booking_id}/assign", response_model=BookingDetail, tags=["admin: bookings"])
def assign(booking_id: uuid.UUID, data: ManualAssignIn, db: DbSession, admin: AdminUser) -> BookingDetail:
    booking = booking_service.get_booking(db, booking_id)
    assignment.manual_assign(db, admin, booking, data.provider_id, data.direct, data.note)
    db.commit()
    db.refresh(booking)
    return _detail(db, booking)


@router.post("/bookings/{booking_id}/status", response_model=BookingDetail, tags=["admin: bookings"])
def set_status(booking_id: uuid.UUID, data: AdminStatusIn, db: DbSession, admin: AdminUser) -> BookingDetail:
    booking = booking_service.get_booking(db, booking_id)
    admin_ops.admin_set_status(db, admin, booking, data.status, data.note)
    db.commit()
    db.refresh(booking)
    return _detail(db, booking)


@router.post("/bookings/{booking_id}/payment", response_model=BookingDetail, tags=["admin: payments"])
def update_payment(booking_id: uuid.UUID, data: PaymentStatusUpdate, db: DbSession, admin: AdminUser) -> BookingDetail:
    booking = booking_service.get_booking(db, booking_id)
    payments.admin_set_payment_status(db, admin, booking, data.status, data.note)
    db.commit()
    db.refresh(booking)
    return _detail(db, booking)


@router.get("/payments", response_model=Page[PaymentRow], tags=["admin: payments"])
def list_payments(
    db: DbSession,
    paging: PagingDep,
    status: PaymentStatus | None = None,
    method: PaymentMethod | None = None,
) -> Page[PaymentRow]:
    stmt = select(Payment).order_by(Payment.created_at.desc())
    if status:
        stmt = stmt.where(Payment.status == status)
    if method:
        stmt = stmt.where(Payment.method == method)
    rows, total = paginate(db, stmt, paging)
    items = [
        PaymentRow(
            id=p.id,
            booking_id=p.booking_id,
            booking_reference=p.booking.reference,
            booking_status=p.booking.status.value,
            customer_name=p.booking.customer.user.full_name,
            provider_name=p.booking.provider.display_name if p.booking.provider else None,
            method=p.method,
            status=p.status,
            amount=p.amount,
            currency=p.currency,
            paid_at=p.paid_at,
            confirmed_by_name=p.confirmed_by.full_name if p.confirmed_by else None,
            created_at=p.created_at,
        )
        for p in rows
    ]
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


def _settlement_row(s: ProviderSettlement) -> SettlementRow:
    return SettlementRow(
        id=s.id,
        booking_id=s.booking_id,
        booking_reference=s.booking.reference,
        provider_id=s.provider_id,
        provider_name=s.provider.display_name,
        gross_amount=s.gross_amount,
        commission_amount=s.commission_amount,
        provider_earning=s.provider_earning,
        cash_collected_by_provider=s.cash_collected_by_provider,
        status=s.status,
        settled_at=s.settled_at,
        reference=s.reference,
        note=s.note,
        created_at=s.created_at,
    )


@router.get("/settlements", response_model=Page[SettlementRow], tags=["admin: settlements"])
def list_settlements(
    db: DbSession, paging: PagingDep, status: SettlementStatus | None = None, provider_id: uuid.UUID | None = None
) -> Page[SettlementRow]:
    stmt = select(ProviderSettlement).order_by(ProviderSettlement.created_at.desc())
    if status:
        stmt = stmt.where(ProviderSettlement.status == status)
    if provider_id:
        stmt = stmt.where(ProviderSettlement.provider_id == provider_id)
    rows, total = paginate(db, stmt, paging)
    return Page(items=[_settlement_row(s) for s in rows], total=total, page=paging.page, page_size=paging.page_size)


@router.post("/settlements/{settlement_id}/settle", response_model=SettlementRow, tags=["admin: settlements"])
def settle(settlement_id: uuid.UUID, data: SettleIn, db: DbSession, admin: AdminUser) -> SettlementRow:
    s = db.get(ProviderSettlement, settlement_id)
    if s is None:
        raise NotFoundError("Settlement not found.")
    payments.settle(db, admin, s, data.reference, data.note)
    db.commit()
    return _settlement_row(s)


@router.get("/complaints", response_model=Page[ComplaintOut], tags=["admin: complaints"])
def list_complaints(db: DbSession, paging: PagingDep, status: ComplaintStatus | None = None) -> Page[ComplaintOut]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc())
    if status:
        stmt = stmt.where(Complaint.status == status)
    rows, total = paginate(db, stmt, paging)
    return Page(
        items=[feedback.complaint_out(c) for c in rows], total=total, page=paging.page, page_size=paging.page_size
    )


@router.patch("/complaints/{complaint_id}", response_model=ComplaintOut, tags=["admin: complaints"])
def update_complaint(complaint_id: uuid.UUID, data: ComplaintUpdate, db: DbSession, admin: AdminUser) -> ComplaintOut:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise NotFoundError("Complaint not found.")
    feedback.update_complaint(db, admin, c, data)
    db.commit()
    return feedback.complaint_out(c)


@router.get("/reviews", response_model=Page[ReviewOut], tags=["admin: reviews"])
def list_reviews(db: DbSession, paging: PagingDep, provider_id: uuid.UUID | None = None) -> Page[ReviewOut]:
    stmt = select(Review).order_by(Review.created_at.desc())
    if provider_id:
        stmt = stmt.where(Review.provider_id == provider_id)
    rows, total = paginate(db, stmt, paging)
    return Page(items=[feedback.review_out(r) for r in rows], total=total, page=paging.page, page_size=paging.page_size)


@router.patch("/reviews/{review_id}", response_model=ReviewOut, tags=["admin: reviews"])
def moderate_review(review_id: uuid.UUID, data: ReviewModerate, db: DbSession, admin: AdminUser) -> ReviewOut:
    r = db.get(Review, review_id)
    if r is None:
        raise NotFoundError("Review not found.")
    feedback.moderate_review(db, admin, r, data.is_hidden, data.moderation_note)
    db.commit()
    return feedback.review_out(r)
