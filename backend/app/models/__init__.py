"""Import every model so SQLAlchemy and Alembic see the full metadata."""

from app.models.booking import Booking, BookingPriceItem, BookingStatusHistory, ProviderAssignment
from app.models.catalog import City, Service, ServiceArea, ServiceOption
from app.models.feedback import Complaint, Review
from app.models.payment import Payment, PaymentGatewayEvent, ProviderSettlement
from app.models.provider import (
    Provider,
    ProviderAvailability,
    ProviderService,
    ProviderServiceArea,
    ProviderVerification,
)
from app.models.system import AuditLog, Notification, PlatformSetting
from app.models.user import Customer, RefreshToken, Role, User

__all__ = [
    "AuditLog",
    "Booking",
    "BookingPriceItem",
    "BookingStatusHistory",
    "City",
    "Complaint",
    "Customer",
    "Notification",
    "Payment",
    "PaymentGatewayEvent",
    "PlatformSetting",
    "Provider",
    "ProviderAssignment",
    "ProviderAvailability",
    "ProviderService",
    "ProviderServiceArea",
    "ProviderSettlement",
    "ProviderVerification",
    "RefreshToken",
    "Review",
    "Role",
    "Service",
    "ServiceArea",
    "ServiceOption",
    "User",
]
