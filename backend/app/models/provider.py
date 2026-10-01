import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.catalog import Service, ServiceArea
from app.models.enums import ProviderType, VerificationDecision, VerificationStatus, db_enum
from app.models.user import User


class Provider(UUIDPk, Timestamped, Base):
    """An individual cleaner or a cleaning company. Companies manage their own staff."""

    __tablename__ = "providers"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="capacity_positive"),
        CheckConstraint("rating_count >= 0", name="rating_count_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider_type: Mapped[ProviderType] = mapped_column(db_enum(ProviderType, "provider_type"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(60))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        db_enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Provider-controlled "I'm taking jobs" switch.
    is_accepting_jobs: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Number of jobs that can run at the same time (1 for an individual, teams for a company).
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rating_average: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal(0), nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="provider", lazy="joined")
    services: Mapped[list["ProviderService"]] = relationship(cascade="all, delete-orphan")
    areas: Mapped[list["ProviderServiceArea"]] = relationship(cascade="all, delete-orphan")
    availability: Mapped[list["ProviderAvailability"]] = relationship(
        cascade="all, delete-orphan", order_by="ProviderAvailability.day_of_week"
    )
    verifications: Mapped[list["ProviderVerification"]] = relationship(
        order_by="ProviderVerification.created_at.desc()", cascade="all, delete-orphan"
    )


class ProviderVerification(UUIDPk, Base):
    """Immutable history of verification decisions."""

    __tablename__ = "provider_verifications"

    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    decision: Mapped[VerificationDecision] = mapped_column(
        db_enum(VerificationDecision, "verification_decision"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reviewed_by: Mapped[User | None] = relationship()


class ProviderService(Base):
    __tablename__ = "provider_services"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    service: Mapped[Service] = relationship(lazy="joined")


class ProviderServiceArea(Base):
    __tablename__ = "provider_service_areas"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("service_areas.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    area: Mapped[ServiceArea] = relationship(lazy="joined")


class ProviderAvailability(UUIDPk, Base):
    """Weekly working hours. ``day_of_week`` follows ISO: 1 = Monday … 7 = Sunday."""

    __tablename__ = "provider_availability"
    __table_args__ = (
        UniqueConstraint("provider_id", "day_of_week"),
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="valid_day"),
        CheckConstraint("end_time > start_time", name="valid_window"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
