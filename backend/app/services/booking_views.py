"""Role-aware booking serialisation.

The backend decides what each party may see and do; ``allowed_actions`` lets
web and mobile clients render buttons without re-implementing business rules.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, Complaint, ProviderAssignment
from app.models.enums import (
    TERMINAL_STATUSES,
    AssignmentStatus,
    BookingStatus,
    ComplaintStatus,
    PaymentMethod,
    PaymentStatus,
    RoleCode,
)
from app.schemas.booking import (
    AssignmentSummary,
    BookingDetail,
    BookingSummary,
    OptionRef,
    PartyContact,
    PaymentSummary,
    ProviderPublic,
    QuoteLine,
    ReviewSummary,
    ServiceRef,
    StatusEvent,
)
from app.services.lifecycle import PROVIDER_PROGRESS, Actor, admin_targets, can_transition
from app.services.payments import CASH_CONFIRMABLE_BY_ADMIN, CASH_CONFIRMABLE_BY_PROVIDER

PROVIDER_ACTION_NAMES = {
    BookingStatus.PROVIDER_EN_ROUTE: "MARK_EN_ROUTE",
    BookingStatus.PROVIDER_ARRIVED: "MARK_ARRIVED",
    BookingStatus.SERVICE_IN_PROGRESS: "START_SERVICE",
    BookingStatus.COMPLETED_BY_PROVIDER: "COMPLETE_SERVICE",
}
OPEN_COMPLAINT = (ComplaintStatus.OPEN, ComplaintStatus.IN_REVIEW)


def summary(b: Booking, include_customer: bool = False) -> BookingSummary:
    return BookingSummary(**_summary_fields(b, include_customer))


def _summary_fields(b: Booking, include_customer: bool) -> dict:
    return {
        "id": b.id,
        "reference": b.reference,
        "status": b.status,
        "service": ServiceRef(
            id=b.service.id,
            slug=b.service.slug,
            name_en=b.service.name_en,
            name_sw=b.service.name_sw,
            icon=b.service.icon,
        ),
        "service_name": b.service_name_snapshot,
        "area_id": b.area_id,
        "area_name": b.area.name,
        "scheduled_date": b.scheduled_date,
        "scheduled_start_time": b.scheduled_start_time,
        "estimated_duration_minutes": b.estimated_duration_minutes,
        "total_amount": b.total_amount,
        "currency": b.currency,
        "payment_method": b.payment_method,
        "payment_status": b.payment.status if b.payment else None,
        "provider_name": b.provider.display_name if b.provider else None,
        "customer_name": b.customer.user.full_name if include_customer else None,
        "created_at": b.created_at,
    }


def _option_ref(opt) -> OptionRef | None:
    return OptionRef(id=opt.id, code=opt.code, name_en=opt.name_en, name_sw=opt.name_sw) if opt else None


def bookings_with_open_complaints(db: Session, booking_ids: list) -> set:
    """One query for a whole list of bookings (avoids a per-row lookup in job lists)."""
    if not booking_ids:
        return set()
    return set(
        db.scalars(
            select(Complaint.booking_id).where(
                Complaint.booking_id.in_(booking_ids), Complaint.status.in_(OPEN_COMPLAINT)
            )
        )
    )


def _has_open_complaint(db: Session, b: Booking) -> bool:
    return bool(
        db.scalar(
            select(Complaint.id).where(Complaint.booking_id == b.id, Complaint.status.in_(OPEN_COMPLAINT)).limit(1)
        )
    )


def customer_actions(b: Booking, has_open_complaint: bool) -> list[str]:
    actions = []
    if b.status == BookingStatus.PENDING_CONFIRMATION:
        actions.append("CONFIRM")
    if can_transition(b.status, BookingStatus.CANCELLED, Actor.CUSTOMER):
        actions.append("CANCEL")
    if b.status == BookingStatus.COMPLETED_BY_PROVIDER:
        actions.append("CONFIRM_COMPLETION")
    if b.status in (BookingStatus.CUSTOMER_CONFIRMED, BookingStatus.CLOSED) and b.review is None:
        actions.append("REVIEW")
    if b.provider_id and b.status != BookingStatus.CANCELLED and not has_open_complaint:
        actions.append("REPORT_ISSUE")
    return actions


def _cash_pending(b: Booking) -> bool:
    return bool(b.payment and b.payment.method == PaymentMethod.CASH and b.payment.status == PaymentStatus.PENDING)


def provider_actions(b: Booking, assignment: ProviderAssignment | None, provider_id) -> list[str]:
    if assignment is not None and assignment.status == AssignmentStatus.OFFERED:
        return ["ACCEPT", "REJECT"]
    if b.provider_id != provider_id:
        return []
    actions = []
    nxt = PROVIDER_PROGRESS.get(b.status)
    if nxt:
        actions.append(PROVIDER_ACTION_NAMES[nxt])
    if b.status == BookingStatus.PROVIDER_ASSIGNED:
        actions.append("WITHDRAW")
    if _cash_pending(b) and b.status in CASH_CONFIRMABLE_BY_PROVIDER:
        actions.append("CONFIRM_CASH")
    return actions


def admin_actions(b: Booking) -> list[str]:
    from app.services.assignment import MANUAL_ASSIGNABLE

    actions = [f"SET_STATUS:{s.value}" for s in admin_targets(b.status) if s != BookingStatus.PROVIDER_ASSIGNED]
    if b.status in MANUAL_ASSIGNABLE:
        actions.append("ASSIGN")
    if _cash_pending(b) and b.status in CASH_CONFIRMABLE_BY_ADMIN:
        actions.append("CONFIRM_CASH")
    return actions


def detail(
    db: Session,
    b: Booking,
    viewer_role: RoleCode,
    *,
    provider_id=None,
    assignment: ProviderAssignment | None = None,
    open_complaint: bool | None = None,
) -> BookingDetail:
    is_admin = viewer_role == RoleCode.ADMIN
    is_customer = viewer_role == RoleCode.CUSTOMER
    is_assigned_provider = viewer_role == RoleCode.PROVIDER and b.provider_id == provider_id
    if open_complaint is None:
        open_complaint = _has_open_complaint(db, b)

    # Location and customer contact are only revealed once a provider has accepted the job.
    reveal_customer = is_admin or (is_assigned_provider and b.status not in TERMINAL_STATUSES)
    show_address = is_admin or is_customer or is_assigned_provider

    provider_public = None
    if b.provider:
        p = b.provider
        provider_public = ProviderPublic(
            id=p.id,
            display_name=p.display_name,
            provider_type=p.provider_type,
            rating_average=p.rating_average,
            rating_count=p.rating_count,
            years_experience=p.years_experience,
            phone=p.user.phone if (is_admin or (is_customer and b.status not in TERMINAL_STATUSES)) else None,
        )

    customer_contact = None
    if is_admin or is_assigned_provider:
        u = b.customer.user
        customer_contact = PartyContact(
            id=u.id,
            full_name=u.full_name,
            phone=u.phone if reveal_customer else None,
            email=u.email if is_admin else None,
        )

    history = [
        StatusEvent(
            from_status=h.from_status,
            to_status=h.to_status,
            note=h.note,
            actor_name=h.changed_by.full_name if (h.changed_by and not is_customer) else None,
            actor_role=h.changed_by.role_code.value if h.changed_by else "SYSTEM",
            created_at=h.created_at,
        )
        for h in b.status_history
    ]

    if is_admin:
        actions = admin_actions(b)
    elif is_customer:
        actions = customer_actions(b, open_complaint)
    else:
        actions = provider_actions(b, assignment, provider_id)

    payment = None
    if b.payment:
        payment = PaymentSummary.model_validate(b.payment)
        payment.confirmed_by_name = b.payment.confirmed_by.full_name if b.payment.confirmed_by else None

    review = None
    if b.review and (is_admin or not b.review.is_hidden or is_customer):
        review = ReviewSummary.model_validate(b.review)

    show_economics = is_admin or is_assigned_provider or (assignment is not None)
    return BookingDetail(
        **_summary_fields(b, include_customer=is_admin or is_assigned_provider),
        address_line=b.address_line if show_address else None,
        landmark=b.landmark if show_address else None,
        bedrooms=b.bedrooms,
        bathrooms=b.bathrooms,
        property_type=_option_ref(b.property_type_option),
        size=_option_ref(b.size_option),
        special_instructions=b.special_instructions,
        base_amount=b.base_amount,
        adjustments_amount=b.adjustments_amount,
        commission_percent=b.commission_percent if show_economics else None,
        commission_amount=b.commission_amount if show_economics else None,
        provider_earning=b.provider_earning if show_economics else None,
        price_items=[
            QuoteLine(
                kind=i.kind,
                code=i.code,
                label_en=i.label_en,
                label_sw=i.label_sw,
                quantity=i.quantity,
                unit_amount=i.unit_amount,
                amount=i.amount,
            )
            for i in b.price_items
        ],
        history=history,
        provider=provider_public,
        customer=customer_contact,
        payment=payment,
        review=review,
        assignments=[
            AssignmentSummary(
                id=a.id,
                provider_id=a.provider_id,
                provider_name=a.provider.display_name,
                status=a.status,
                is_manual=a.is_manual,
                offered_at=a.offered_at,
                expires_at=a.expires_at,
                responded_at=a.responded_at,
                response_note=a.response_note,
            )
            for a in b.assignments
        ]
        if is_admin
        else None,
        has_open_complaint=open_complaint,
        allowed_actions=actions,
        confirmed_at=b.confirmed_at,
        completed_at=b.completed_at,
        customer_confirmed_at=b.customer_confirmed_at,
        closed_at=b.closed_at,
        cancelled_at=b.cancelled_at,
        cancellation_reason=b.cancellation_reason,
    )
