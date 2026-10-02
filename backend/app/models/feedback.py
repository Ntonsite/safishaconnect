import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.booking import Booking
from app.models.enums import ComplaintCategory, ComplaintStatus, db_enum
from app.models.provider import Provider
from app.models.user import Customer, User


class Review(UUIDPk, Timestamped, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        # Landing-page testimonials: newest visible reviews.
        Index("ix_reviews_visible_recent", "created_at", postgresql_where=text("is_hidden = false")),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    moderation_note: Mapped[str | None] = mapped_column(String(255))
    moderated_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))

    booking: Mapped[Booking] = relationship(back_populates="review")
    customer: Mapped[Customer] = relationship(lazy="joined")
    provider: Mapped[Provider] = relationship(lazy="joined")


class Complaint(UUIDPk, Timestamped, Base):
    __tablename__ = "complaints"

    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    category: Mapped[ComplaintCategory] = mapped_column(db_enum(ComplaintCategory, "complaint_category"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ComplaintStatus] = mapped_column(
        db_enum(ComplaintStatus, "complaint_status"), default=ComplaintStatus.OPEN, nullable=False, index=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    booking: Mapped[Booking] = relationship(lazy="joined")
    customer: Mapped[Customer] = relationship(lazy="joined")
    resolved_by: Mapped[User | None] = relationship()
