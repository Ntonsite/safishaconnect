"""Time helpers. Bookings are scheduled in the platform's local timezone."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def local_now() -> datetime:
    return datetime.now(local_tz())


def local_today() -> date:
    return local_now().date()


def to_local_datetime(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=local_tz())


def add_minutes(at: time, minutes: int) -> time:
    """Add minutes to a time of day, clamping at 23:59 (jobs never cross midnight)."""
    total = at.hour * 60 + at.minute + minutes
    total = min(total, 23 * 60 + 59)
    return time(total // 60, total % 60)


def minutes_of(at: time) -> int:
    return at.hour * 60 + at.minute


def overlaps(start_a: time, minutes_a: int, start_b: time, minutes_b: int) -> bool:
    a0, b0 = minutes_of(start_a), minutes_of(start_b)
    return a0 < b0 + minutes_b and b0 < a0 + minutes_a


def expires_in(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)
