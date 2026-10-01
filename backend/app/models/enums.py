"""Domain enumerations.

Stored as VARCHAR + CHECK constraints (``native_enum=False``) so new values can be
added with a simple migration rather than PostgreSQL ``ALTER TYPE`` gymnastics.
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def db_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


class RoleCode(StrEnum):
    CUSTOMER = "CUSTOMER"
    PROVIDER = "PROVIDER"
    ADMIN = "ADMIN"


class ProviderType(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class VerificationDecision(StrEnum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REACTIVATED = "REACTIVATED"


class OptionGroup(StrEnum):
    PROPERTY_TYPE = "PROPERTY_TYPE"
    SIZE = "SIZE"
    ADDON = "ADDON"


class BookingStatus(StrEnum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    FINDING_PROVIDER = "FINDING_PROVIDER"
    PROVIDER_ASSIGNED = "PROVIDER_ASSIGNED"
    PROVIDER_EN_ROUTE = "PROVIDER_EN_ROUTE"
    PROVIDER_ARRIVED = "PROVIDER_ARRIVED"
    SERVICE_IN_PROGRESS = "SERVICE_IN_PROGRESS"
    COMPLETED_BY_PROVIDER = "COMPLETED_BY_PROVIDER"
    CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REASSIGNMENT_REQUIRED = "REASSIGNMENT_REQUIRED"
    DISPUTED = "DISPUTED"


class AssignmentStatus(StrEnum):
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    WITHDRAWN = "WITHDRAWN"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"
    CARD = "CARD"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"  # booking cancelled before any money changed hands


class SettlementStatus(StrEnum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class ComplaintCategory(StrEnum):
    QUALITY = "QUALITY"
    LATE_OR_NO_SHOW = "LATE_OR_NO_SHOW"
    DAMAGE = "DAMAGE"
    CONDUCT = "CONDUCT"
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"


class ComplaintStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    SMS = "SMS"
    PUSH = "PUSH"


# Statuses in which a provider is committed to (and occupied by) a booking.
ACTIVE_ASSIGNED_STATUSES = frozenset(
    {
        BookingStatus.PROVIDER_ASSIGNED,
        BookingStatus.PROVIDER_EN_ROUTE,
        BookingStatus.PROVIDER_ARRIVED,
        BookingStatus.SERVICE_IN_PROGRESS,
    }
)

TERMINAL_STATUSES = frozenset({BookingStatus.CLOSED, BookingStatus.CANCELLED})
