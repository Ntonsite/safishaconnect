import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.catalog import Money, Service, ServiceArea, ServiceOption
from app.models.enums import AssignmentStatus, BookingStatus, PaymentMethod, db_enum
from app.models.provider import Provider
from app.models.user import Customer, User


class Booking(UUIDPk, Timestamped, Base):
    """A customer booking with an immutable pricing/commission snapshot."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
        CheckConstraint("commission_amount + provider_earning = total_amount", name="economics_balance"),
        CheckConstraint("bedrooms >= 0 AND bathrooms >= 0", name="rooms_non_negative"),
        Index("ix_bookings_provider_schedule", "provider_id", "scheduled_date"),
    )

    reference: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("services.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_areas.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("providers.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        db_enum(BookingStatus, "booking_status"), default=BookingStatus.PENDING_CONFIRMATION, index=True
    )

    # Location & property details
    address_line: Mapped[str] = mapped_column(String(255), nullable=False)
    landmark: Mapped[str | None] = mapped_column(String(255))
    property_type_option_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("service_options.id", ondelete="RESTRICT")
    )
    size_option_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("service_options.id", ondelete="RESTRICT")
    )
    bedrooms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    special_instructions: Mapped[str | None] = mapped_column(Text)

    # Schedule (local Africa/Dar_es_Salaam time)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    scheduled_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Pricing snapshot
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    service_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    adjustments_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    provider_earning: Mapped[Decimal] = mapped_column(Money, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(db_enum(PaymentMethod, "payment_method"), nullable=False)

    # Lifecycle timestamps
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))

    customer: Mapped[Customer] = relationship(lazy="joined")
    service: Mapped[Service] = relationship(lazy="joined")
    area: Mapped[ServiceArea] = relationship(lazy="joined")
    provider: Mapped[Provider | None] = relationship(lazy="joined")
    property_type_option: Mapped[ServiceOption | None] = relationship(foreign_keys=[property_type_option_id])
    size_option: Mapped[ServiceOption | None] = relationship(foreign_keys=[size_option_id])
    price_items: Mapped[list["BookingPriceItem"]] = relationship(
        cascade="all, delete-orphan", order_by="BookingPriceItem.position"
    )
    status_history: Mapped[list["BookingStatusHistory"]] = relationship(
        cascade="all, delete-orphan", order_by="BookingStatusHistory.created_at"
    )
    assignments: Mapped[list["ProviderAssignment"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="ProviderAssignment.offered_at"
    )
    payment: Mapped["Payment | None"] = relationship(back_populates="booking", uselist=False)  # noqa: F821
    review: Mapped["Review | None"] = relationship(back_populates="booking", uselist=False)  # noqa: F821


class BookingPriceItem(UUIDPk, Base):
    """Line items that make up the quoted price (base, extras, options, add-ons)."""

    __tablename__ = "booking_price_items"

    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label_en: Mapped[str] = mapped_column(String(160), nullable=False)
    label_sw: Mapped[str] = mapped_column(String(160), nullable=False)
    option_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("service_options.id", ondelete="SET NULL"))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)


class BookingStatusHistory(UUIDPk, Base):
    __tablename__ = "booking_status_history"

    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[BookingStatus | None] = mapped_column(db_enum(BookingStatus, "from_booking_status"))
    to_status: Mapped[BookingStatus] = mapped_column(db_enum(BookingStatus, "booking_status"), nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    changed_by: Mapped[User | None] = relationship(lazy="joined")


class ProviderAssignment(UUIDPk, Timestamped, Base):
    """A job offer to a provider. At most one OFFERED/ACCEPTED assignment per booking at a time."""

    __tablename__ = "provider_assignments"
    __table_args__ = (Index("ix_assignments_provider_status", "provider_id", "status"),)

    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("providers.id", ondelete="CASCADE"))
    status: Mapped[AssignmentStatus] = mapped_column(
        db_enum(AssignmentStatus, "assignment_status"), default=AssignmentStatus.OFFERED, nullable=False
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_note: Mapped[str | None] = mapped_column(String(255))

    booking: Mapped[Booking] = relationship(back_populates="assignments")
    provider: Mapped[Provider] = relationship(lazy="joined")
