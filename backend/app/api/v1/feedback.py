"""Customer reviews and complaints."""

import uuid

from fastapi import APIRouter, status
from pydantic import Field
from sqlalchemy import select

from app.models import Complaint, Review
from app.schemas.feedback import ComplaintCreate, ComplaintOut, ReviewCreate, ReviewOut
from app.security.deps import CurrentCustomer, DbSession
from app.services import bookings as booking_service
from app.services import feedback

reviews = APIRouter(prefix="/reviews", tags=["reviews"])
complaints = APIRouter(prefix="/complaints", tags=["complaints"])


class ReviewIn(ReviewCreate):
    booking_id: uuid.UUID = Field(description="Booking being reviewed")


@reviews.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(data: ReviewIn, customer: CurrentCustomer, db: DbSession) -> ReviewOut:
    booking = booking_service.get_customer_booking(db, customer, data.booking_id)
    review = feedback.create_review(db, customer, booking, data)
    db.commit()
    db.refresh(review)
    return feedback.review_out(review)


@reviews.get("/mine", response_model=list[ReviewOut])
def my_reviews(customer: CurrentCustomer, db: DbSession) -> list[ReviewOut]:
    rows = db.scalars(select(Review).where(Review.customer_id == customer.id).order_by(Review.created_at.desc()))
    return [feedback.review_out(r) for r in rows.unique()]


@complaints.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(data: ComplaintCreate, customer: CurrentCustomer, db: DbSession) -> ComplaintOut:
    booking = booking_service.get_customer_booking(db, customer, data.booking_id)
    complaint = feedback.create_complaint(db, customer, booking, data)
    db.commit()
    db.refresh(complaint)
    return feedback.complaint_out(complaint)


@complaints.get("", response_model=list[ComplaintOut])
def my_complaints(customer: CurrentCustomer, db: DbSession) -> list[ComplaintOut]:
    rows = db.scalars(
        select(Complaint).where(Complaint.customer_id == customer.id).order_by(Complaint.created_at.desc())
    )
    return [feedback.complaint_out(c) for c in rows.unique()]
