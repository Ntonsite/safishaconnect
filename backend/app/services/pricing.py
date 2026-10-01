"""Pricing engine — the single source of truth for customer prices.

    customer price = base price
                   + extra bedrooms/bathrooms beyond those included
                   + property type modifier
                   + size band modifier
                   + Σ add-on price × quantity

Commission is a configurable percentage; provider earning is the remainder.
All arithmetic uses ``Decimal`` rounded to whole shillings.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationFailedError
from app.models import Service, ServiceOption
from app.models.enums import OptionGroup
from app.schemas.booking import QuoteRequest
from app.utils.money import percent_of, tzs


@dataclass
class PriceLine:
    kind: str
    code: str
    label_en: str
    label_sw: str
    quantity: int
    unit_amount: Decimal
    amount: Decimal
    option_id: uuid.UUID | None = None


@dataclass
class Quote:
    service: Service
    currency: str
    lines: list[PriceLine] = field(default_factory=list)
    duration_minutes: int = 0
    property_type: ServiceOption | None = None
    size: ServiceOption | None = None
    bedrooms: int = 0
    bathrooms: int = 0

    @property
    def base_amount(self) -> Decimal:
        return sum((ln.amount for ln in self.lines if ln.kind == "BASE"), Decimal(0))

    @property
    def adjustments_amount(self) -> Decimal:
        return sum((ln.amount for ln in self.lines if ln.kind != "BASE"), Decimal(0))

    @property
    def total_amount(self) -> Decimal:
        return tzs(self.base_amount + self.adjustments_amount)


@dataclass(frozen=True)
class Economics:
    commission_percent: Decimal
    commission_amount: Decimal
    provider_earning: Decimal


def split_commission(total: Decimal, commission_percent: Decimal) -> Economics:
    commission = percent_of(total, commission_percent)
    return Economics(commission_percent, commission, tzs(total - commission))


def _option(service: Service, option_id: uuid.UUID, group: OptionGroup) -> ServiceOption:
    for opt in service.options:
        if opt.id == option_id:
            if opt.group != group or not opt.is_active:
                break
            return opt
    raise ValidationFailedError("Selected option is not available for this service.", code="INVALID_OPTION")


def calculate_quote(db: Session, request: QuoteRequest) -> Quote:
    service = db.get(Service, request.service_id)
    if service is None or not service.is_active:
        raise NotFoundError("This service is not available.", code="SERVICE_NOT_FOUND")

    quote = Quote(service=service, currency=get_settings().default_currency)
    quote.lines.append(
        PriceLine("BASE", "base", service.name_en, service.name_sw, 1, tzs(service.base_price), tzs(service.base_price))
    )
    quote.duration_minutes = service.base_duration_minutes

    if service.uses_rooms:
        if request.bedrooms > service.max_rooms or request.bathrooms > service.max_rooms:
            raise ValidationFailedError(
                f"For more than {service.max_rooms} rooms please contact us for a custom quote.", code="TOO_MANY_ROOMS"
            )
        if request.bathrooms < 1:
            raise ValidationFailedError("Please tell us how many bathrooms there are.", code="BATHROOMS_REQUIRED")
        quote.bedrooms, quote.bathrooms = request.bedrooms, request.bathrooms
        extra_bed = max(0, request.bedrooms - service.included_bedrooms)
        extra_bath = max(0, request.bathrooms - service.included_bathrooms)
        if extra_bed:
            unit = tzs(service.price_per_extra_bedroom)
            quote.lines.append(
                PriceLine(
                    "EXTRA_ROOMS",
                    "extra_bedrooms",
                    "Extra bedrooms",
                    "Vyumba vya ziada vya kulala",
                    extra_bed,
                    unit,
                    unit * extra_bed,
                )
            )
        if extra_bath:
            unit = tzs(service.price_per_extra_bathroom)
            quote.lines.append(
                PriceLine(
                    "EXTRA_ROOMS",
                    "extra_bathrooms",
                    "Extra bathrooms",
                    "Mabafu ya ziada",
                    extra_bath,
                    unit,
                    unit * extra_bath,
                )
            )
        quote.duration_minutes += (extra_bed + extra_bath) * service.minutes_per_extra_room

    groups = {opt.group for opt in service.options if opt.is_active}
    for group, selected_id, kind in (
        (OptionGroup.PROPERTY_TYPE, request.property_type_option_id, "PROPERTY_TYPE"),
        (OptionGroup.SIZE, request.size_option_id, "SIZE"),
    ):
        if selected_id is None:
            if group in groups:
                raise ValidationFailedError(
                    "Please choose the property type."
                    if group == OptionGroup.PROPERTY_TYPE
                    else "Please choose the size.",
                    code=f"{kind}_REQUIRED",
                )
            continue
        opt = _option(service, selected_id, group)
        if group == OptionGroup.PROPERTY_TYPE:
            quote.property_type = opt
        else:
            quote.size = opt
        quote.duration_minutes += opt.duration_minutes
        if opt.price_amount > 0:
            unit = tzs(opt.price_amount)
            quote.lines.append(PriceLine(kind, opt.code, opt.name_en, opt.name_sw, 1, unit, unit, opt.id))

    seen: set[uuid.UUID] = set()
    for addon in request.addons:
        if addon.option_id in seen:
            raise ValidationFailedError("Each add-on can only be selected once.", code="DUPLICATE_ADDON")
        seen.add(addon.option_id)
        opt = _option(service, addon.option_id, OptionGroup.ADDON)
        if addon.quantity > opt.max_quantity:
            raise ValidationFailedError(
                f"Maximum quantity for {opt.name_en} is {opt.max_quantity}.", code="ADDON_QUANTITY"
            )
        unit = tzs(opt.price_amount)
        quote.lines.append(
            PriceLine("ADDON", opt.code, opt.name_en, opt.name_sw, addon.quantity, unit, unit * addon.quantity, opt.id)
        )
        quote.duration_minutes += opt.duration_minutes * addon.quantity

    return quote
