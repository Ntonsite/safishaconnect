"""Admin-editable platform settings with typed accessors and env-backed defaults."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationFailedError
from app.models import PlatformSetting


@dataclass(frozen=True)
class SettingSpec:
    key: str
    description: str
    kind: type
    minimum: Decimal
    maximum: Decimal

    def default(self) -> str:
        s = get_settings()
        return {
            "commission_percent": str(s.default_commission_percent),
            "assignment_offer_ttl_minutes": str(s.assignment_offer_ttl_minutes),
            "min_booking_lead_hours": str(s.min_booking_lead_hours),
            "max_booking_days_ahead": str(s.max_booking_days_ahead),
        }[self.key]


SPECS: dict[str, SettingSpec] = {
    spec.key: spec
    for spec in (
        SettingSpec(
            "commission_percent", "Platform commission as a % of the customer price", Decimal, Decimal(0), Decimal(60)
        ),
        SettingSpec(
            "assignment_offer_ttl_minutes",
            "Minutes a provider has to respond to a job offer",
            int,
            Decimal(5),
            Decimal(1440),
        ),
        SettingSpec(
            "min_booking_lead_hours", "Minimum hours between booking and service start", int, Decimal(0), Decimal(72)
        ),
        SettingSpec("max_booking_days_ahead", "How many days ahead customers can book", int, Decimal(1), Decimal(365)),
    )
}


def _raw(db: Session, key: str) -> str:
    row = db.get(PlatformSetting, key)
    return row.value if row else SPECS[key].default()


def commission_percent(db: Session) -> Decimal:
    return Decimal(_raw(db, "commission_percent"))


def offer_ttl_minutes(db: Session) -> int:
    return int(_raw(db, "assignment_offer_ttl_minutes"))


def min_lead_hours(db: Session) -> int:
    return int(_raw(db, "min_booking_lead_hours"))


def max_days_ahead(db: Session) -> int:
    return int(_raw(db, "max_booking_days_ahead"))


def list_settings(db: Session) -> list[dict]:
    return [{"key": k, "value": _raw(db, k), "description": s.description} for k, s in SPECS.items()]


def update_setting(db: Session, key: str, value: str, actor_id) -> tuple[str, str]:
    spec = SPECS.get(key)
    if spec is None:
        raise ValidationFailedError(f"Unknown setting '{key}'.")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationFailedError("Setting value must be a number.") from exc
    if spec.kind is int and parsed != parsed.to_integral_value():
        raise ValidationFailedError("Setting value must be a whole number.")
    if not (spec.minimum <= parsed <= spec.maximum):
        raise ValidationFailedError(f"Value must be between {spec.minimum} and {spec.maximum}.")
    normalised = str(int(parsed)) if spec.kind is int else str(parsed.normalize())
    old = _raw(db, key)
    row = db.get(PlatformSetting, key)
    if row is None:
        row = PlatformSetting(key=key, value=normalised, description=spec.description)
        db.add(row)
    row.value = normalised
    row.updated_by_id = actor_id
    return old, normalised
