"""Reviews and complaints."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationFailedError
from app.core.logging import get_logger
from app.models import Booking, Complaint, Customer, Review, User
from app.models.enums import BookingStatus, ComplaintStatus
from app.schemas.feedback import ComplaintCreate, ComplaintOut, ComplaintUpdate, ReviewCreate, ReviewOut
from app.services import audit
from app.services.lifecycle import Actor, transition
from app.services.notifications import notify_admins
from app.services.provider_profile import recalculate_rating
from app.utils.clock import utcnow

log = get_logger("feedback")

REVIEWABLE = (BookingStatus.CUSTOMER_CONFIRMED, BookingStatus.CLOSED)


def review_out(r: Review) -> ReviewOut:
    return ReviewOut(
        id=r.id,
        booking_id=r.booking_id,
        booking_reference=r.booking.reference,
        service_name=r.booking.service_name_snapshot,
        provider_id=r.provider_id,
        provider_name=r.provider.display_name,
        customer_name=r.customer.user.full_name,
        rating=r.rating,
        comment=r.comment,
        is_hidden=r.is_hidden,
        moderation_note=r.moderation_note,
        created_at=r.created_at,
    )


def create_review(db: Session, customer: Customer, booking: Booking, data: ReviewCreate) -> Review:
    if booking.status not in REVIEWABLE or booking.provider_id is None:
        raise ValidationFailedError("You can review a booking once the service is complete.", code="NOT_REVIEWABLE")
    if db.scalar(select(Review.id).where(Review.booking_id == booking.id)):
        raise ConflictError("You have already reviewed this booking.", code="DUPLICATE_REVIEW")
    review = Review(
        booking_id=booking.id,
        customer_id=customer.id,
        provider_id=booking.provider_id,
        rating=data.rating,
        comment=(data.comment or "").strip() or None,
    )
    db.add(review)
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent duplicate submission
        db.rollback()
        raise ConflictError("You have already reviewed this booking.", code="DUPLICATE_REVIEW") from exc
    recalculate_rating(db, booking.provider)
    log.info("review.created", extra={"booking": booking.reference, "rating": data.rating})
    return review


def moderate_review(db: Session, admin: User, review: Review, is_hidden: bool, note: str | None) -> None:
    review.is_hidden = is_hidden
    review.moderation_note = note
    review.moderated_by_id = admin.id
    db.flush()
    recalculate_rating(db, review.provider)
    audit.record(
        db,
        admin,
        "ADMIN_MODERATED_REVIEW",
        "review",
        review.id,
        {"booking": review.booking.reference, "hidden": is_hidden, "note": note},
    )


def complaint_out(c: Complaint) -> ComplaintOut:
    b = c.booking
    return ComplaintOut(
        id=c.id,
        booking_id=b.id,
        booking_reference=b.reference,
        booking_status=b.status.value,
        customer_name=c.customer.user.full_name,
        provider_name=b.provider.display_name if b.provider else None,
        category=c.category,
        description=c.description,
        status=c.status,
        admin_notes=c.admin_notes,
        resolution=c.resolution,
        resolved_at=c.resolved_at,
        created_at=c.created_at,
    )


def create_complaint(db: Session, customer: Customer, booking: Booking, data: ComplaintCreate) -> Complaint:
    if booking.provider_id is None or booking.status == BookingStatus.CANCELLED:
        raise ValidationFailedError("Issues can be reported once a provider is assigned.", code="NOT_COMPLAINABLE")
    open_exists = db.scalar(
        select(Complaint.id).where(
            Complaint.booking_id == booking.id, Complaint.status.in_((ComplaintStatus.OPEN, ComplaintStatus.IN_REVIEW))
        )
    )
    if open_exists:
        raise ConflictError("There is already an open issue for this booking.", code="COMPLAINT_ALREADY_OPEN")
    complaint = Complaint(
        booking_id=booking.id, customer_id=customer.id, category=data.category, description=data.description.strip()
    )
    db.add(complaint)
    # Reporting a problem instead of confirming completion puts the booking in dispute.
    if booking.status == BookingStatus.COMPLETED_BY_PROVIDER:
        transition(db, booking, BookingStatus.DISPUTED, Actor.CUSTOMER, customer.user, note=f"Issue: {data.category}")
    notify_admins(db, "ADMIN_COMPLAINT", booking)
    log.info("complaint.created", extra={"booking": booking.reference, "category": data.category})
    return complaint


def update_complaint(db: Session, admin: User, complaint: Complaint, data: ComplaintUpdate) -> None:
    old = complaint.status
    complaint.status = data.status
    if data.admin_notes is not None:
        complaint.admin_notes = data.admin_notes
    if data.resolution is not None:
        complaint.resolution = data.resolution
    if data.status in (ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED):
        if not complaint.resolution:
            raise ValidationFailedError("Please describe the resolution.", code="RESOLUTION_REQUIRED")
        complaint.resolved_at = utcnow()
        complaint.resolved_by_id = admin.id
    else:
        complaint.resolved_at = None
        complaint.resolved_by_id = None
    audit.record(
        db,
        admin,
        "ADMIN_UPDATED_COMPLAINT",
        "complaint",
        complaint.id,
        {"booking": complaint.booking.reference, "from": old, "to": data.status},
    )
