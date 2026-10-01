"""Locations, services and the configurable pricing catalogue."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.enums import OptionGroup, db_enum

Money = Numeric(12, 2)


class City(UUIDPk, Timestamped, Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("name", "country_code"),)

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), default="TZ", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    areas: Mapped[list["ServiceArea"]] = relationship(back_populates="city", order_by="ServiceArea.name")


class ServiceArea(UUIDPk, Timestamped, Base):
    __tablename__ = "service_areas"
    __table_args__ = (UniqueConstraint("city_id", "name"),)

    city_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    city: Mapped[City] = relationship(back_populates="areas", lazy="joined")

    @property
    def city_name(self) -> str:
        return self.city.name


class Service(UUIDPk, Timestamped, Base):
    """A cleaning service. Customer price = base + room extras + selected options."""

    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="base_price_non_negative"),
        CheckConstraint("base_duration_minutes > 0", name="duration_positive"),
    )

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_sw: Mapped[str] = mapped_column(String(120), nullable=False)
    summary_en: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    summary_sw: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description_en: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_sw: Mapped[str] = mapped_column(Text, default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="sparkles", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    base_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    base_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Room-based pricing. When ``uses_rooms`` is false bedrooms/bathrooms are not asked for.
    uses_rooms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    included_bedrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    included_bathrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price_per_extra_bedroom: Mapped[Decimal] = mapped_column(Money, default=Decimal(0), nullable=False)
    price_per_extra_bathroom: Mapped[Decimal] = mapped_column(Money, default=Decimal(0), nullable=False)
    minutes_per_extra_room: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_rooms: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    options: Mapped[list["ServiceOption"]] = relationship(
        back_populates="service", order_by="ServiceOption.display_order"
    )


class ServiceOption(UUIDPk, Timestamped, Base):
    """A priced modifier: property type, size band, or optional add-on."""

    __tablename__ = "service_options"
    __table_args__ = (
        UniqueConstraint("service_id", "code"),
        CheckConstraint("price_amount >= 0", name="price_non_negative"),
        CheckConstraint("max_quantity >= 1", name="max_quantity_positive"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("services.id", ondelete="CASCADE"), index=True)
    group: Mapped[OptionGroup] = mapped_column(db_enum(OptionGroup, "option_group"), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_sw: Mapped[str] = mapped_column(String(120), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal(0), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # For add-ons priced per unit (e.g. per sofa seat).
    max_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    service: Mapped[Service] = relationship(back_populates="options")
