import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
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
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        # A gateway transaction can only ever settle one payment.
        Index(
            "uq_payments_gateway_reference",
            "gateway",
            "gateway_reference",
            unique=True,
            postgresql_where=text("gateway_reference IS NOT NULL"),
        ),
        Index("ix_payments_created_at", "created_at"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(db_enum(PaymentMethod, "payment_method"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        db_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING, nullable=False, index=True
    )
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    __mapper_args__ = {"version_id_col": version_id}  # noqa: RUF012
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
    __table_args__ = (Index("ix_provider_settlements_created_at", "created_at"),)

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
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    __mapper_args__ = {"version_id_col": version_id}  # noqa: RUF012
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    reference: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    booking: Mapped[Booking] = relationship(lazy="joined")
    provider: Mapped[Provider] = relationship(lazy="joined")


class PaymentGatewayEvent(UUIDPk, Base):
    """Append-only ledger of payment-provider callbacks (M-Pesa, Airtel Money, card acquirer...).

    Gateways retry callbacks, so the same notification can arrive several times. The
    unique ``(gateway, dedupe_key)`` constraint makes recording idempotent: the first
    copy is processed, later copies are acknowledged and ignored.
    """

    __tablename__ = "payment_gateway_events"
    __table_args__ = (Index("uq_payment_gateway_events_dedupe", "gateway", "dedupe_key", unique=True),)

    gateway: Mapped[str] = mapped_column(String(40), nullable=False)
    # The gateway's own event/callback id when it has one, else "<transaction id>:<status>".
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    external_transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str | None] = mapped_column(String(3))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="SET NULL"), index=True
    )
    # Processing outcome: APPLIED, ALREADY_APPLIED, AMOUNT_MISMATCH, UNKNOWN_PAYMENT, NOT_PAYABLE, RECORDED.
    outcome: Mapped[str | None] = mapped_column(String(60))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
