import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import OptionGroup
from app.schemas.common import ORMModel


class AreaOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    city_id: uuid.UUID
    city_name: str
    is_active: bool


class CityOut(ORMModel):
    id: uuid.UUID
    name: str
    region: str
    country_code: str
    is_active: bool


class ServiceOptionOut(ORMModel):
    id: uuid.UUID
    group: OptionGroup
    code: str
    name_en: str
    name_sw: str
    price_amount: Decimal
    duration_minutes: int
    max_quantity: int
    is_active: bool
    display_order: int


class ServiceOut(ORMModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_sw: str
    summary_en: str
    summary_sw: str
    description_en: str
    description_sw: str
    icon: str
    is_active: bool
    display_order: int
    base_price: Decimal
    base_duration_minutes: int
    uses_rooms: bool
    included_bedrooms: int
    included_bathrooms: int
    price_per_extra_bedroom: Decimal
    price_per_extra_bathroom: Decimal
    minutes_per_extra_room: int
    max_rooms: int
    options: list[ServiceOptionOut]


# ---- Admin write models ---------------------------------------------------------------


class ServiceWrite(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name_en: str = Field(min_length=2, max_length=120)
    name_sw: str = Field(min_length=2, max_length=120)
    summary_en: str = Field(default="", max_length=255)
    summary_sw: str = Field(default="", max_length=255)
    description_en: str = Field(default="", max_length=4000)
    description_sw: str = Field(default="", max_length=4000)
    icon: str = Field(default="sparkles", max_length=40)
    is_active: bool = True
    display_order: int = 0
    base_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    base_duration_minutes: int = Field(gt=0, le=24 * 60)
    uses_rooms: bool = True
    included_bedrooms: int = Field(default=1, ge=0, le=20)
    included_bathrooms: int = Field(default=1, ge=0, le=20)
    price_per_extra_bedroom: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    price_per_extra_bathroom: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    minutes_per_extra_room: int = Field(default=0, ge=0, le=240)
    max_rooms: int = Field(default=10, ge=1, le=30)


class ServiceUpdate(BaseModel):
    name_en: str | None = Field(default=None, min_length=2, max_length=120)
    name_sw: str | None = Field(default=None, min_length=2, max_length=120)
    summary_en: str | None = Field(default=None, max_length=255)
    summary_sw: str | None = Field(default=None, max_length=255)
    description_en: str | None = Field(default=None, max_length=4000)
    description_sw: str | None = Field(default=None, max_length=4000)
    icon: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    display_order: int | None = None
    base_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    base_duration_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    uses_rooms: bool | None = None
    included_bedrooms: int | None = Field(default=None, ge=0, le=20)
    included_bathrooms: int | None = Field(default=None, ge=0, le=20)
    price_per_extra_bedroom: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_per_extra_bathroom: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    minutes_per_extra_room: int | None = Field(default=None, ge=0, le=240)
    max_rooms: int | None = Field(default=None, ge=1, le=30)


class ServiceOptionWrite(BaseModel):
    group: OptionGroup
    code: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9_]+$")
    name_en: str = Field(min_length=2, max_length=120)
    name_sw: str = Field(min_length=2, max_length=120)
    price_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    duration_minutes: int = Field(default=0, ge=0, le=600)
    max_quantity: int = Field(default=1, ge=1, le=50)
    is_active: bool = True
    display_order: int = 0


class ServiceOptionUpdate(BaseModel):
    name_en: str | None = Field(default=None, min_length=2, max_length=120)
    name_sw: str | None = Field(default=None, min_length=2, max_length=120)
    price_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    duration_minutes: int | None = Field(default=None, ge=0, le=600)
    max_quantity: int | None = Field(default=None, ge=1, le=50)
    is_active: bool | None = None
    display_order: int | None = None


class CityWrite(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    region: str = Field(min_length=2, max_length=80)
    country_code: str = Field(default="TZ", min_length=2, max_length=2)
    is_active: bool = True


class AreaWrite(BaseModel):
    city_id: uuid.UUID
    name: str = Field(min_length=2, max_length=80)
    is_active: bool = True


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    is_active: bool | None = None
