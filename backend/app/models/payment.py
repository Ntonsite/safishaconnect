import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.booking import Booking
from app.models.catalog import Money
from app.models.enums import PaymentMethod, PaymentStatus, SettlementStatus, db_enum
from app.models.provider import Provider
from app.models.user import User


class Payment(UUIDPk, Timestamped, Base):
    """Customer payment for a booking. Lifecycle is independent of the booking status."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(db_enum(PaymentMethod, "payment_method"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        db_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING, nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    gateway: Mapped[str] = mapped_column(String(40), default="cash", nullable=False)
    gateway_reference: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    booking: Mapped[Booking] = relationship(back_populates="payment")
    confirmed_by: Mapped[User | None] = relationship(lazy="joined")


class ProviderSettlement(UUIDPk, Timestamped, Base):
    """What the platform owes (or has paid) a provider for a closed booking."""

    __tablename__ = "provider_settlements"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("providers.id", ondelete="RESTRICT"), index=True)
    gross_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    provider_earning: Mapped[Decimal] = mapped_column(Money, nullable=False)
    # For cash jobs the provider holds the cash, so the balance flows provider -> platform.
    cash_collected_by_provider: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        db_enum(SettlementStatus, "settlement_status"), default=SettlementStatus.PENDING, nullable=False, index=True
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    reference: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    booking: Mapped[Booking] = relationship(lazy="joined")
    provider: Mapped[Provider] = relationship(lazy="joined")
