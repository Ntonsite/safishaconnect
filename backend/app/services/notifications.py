"""Notification abstraction.

``notify`` always writes an in-app notification. Additional channels (SMS, push)
implement ``NotificationSender`` and are enabled only when credentials are
configured — nothing pretends to send an SMS when no provider exists.
"""

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Booking, Notification, Role, User
from app.models.enums import NotificationChannel, RoleCode

log = get_logger("notifications")

# English fallback text; clients localise by ``type`` using their own translation files.
TEMPLATES: dict[str, tuple[str, str]] = {
    "BOOKING_RECEIVED": ("Booking received", "We received booking {ref}. Please confirm it to start matching."),
    "BOOKING_CONFIRMED": ("Booking confirmed", "Booking {ref} is confirmed. We're finding you a verified provider."),
    "PROVIDER_ASSIGNED": ("Provider assigned", "{provider} will handle booking {ref}."),
    "PROVIDER_EN_ROUTE": ("Provider on the way", "Your provider is on the way for booking {ref}."),
    "PROVIDER_ARRIVED": ("Provider arrived", "Your provider has arrived for booking {ref}."),
    "SERVICE_STARTED": ("Cleaning started", "Cleaning for booking {ref} has started."),
    "SERVICE_COMPLETED": ("Cleaning completed", "Booking {ref} is complete. Please confirm and rate your provider."),
    "PAYMENT_CONFIRMED": ("Payment confirmed", "Payment for booking {ref} has been received. Thank you!"),
    "BOOKING_CLOSED": ("Booking closed", "Booking {ref} is closed."),
    "BOOKING_CANCELLED": ("Booking cancelled", "Booking {ref} has been cancelled."),
    "BOOKING_DELAYED": ("Still matching", "We're still looking for a provider for booking {ref}. Our team is on it."),
    "JOB_OFFERED": ("New job request", "New {service} job in {area} on {when}. Respond before it expires."),
    "JOB_ASSIGNED": ("Job assigned", "You have been assigned booking {ref}."),
    "JOB_CANCELLED": ("Job cancelled", "Booking {ref} was cancelled or reassigned."),
    "JOB_OFFER_EXPIRED": ("Job offer expired", "The offer for booking {ref} expired."),
    "CUSTOMER_CONFIRMED": ("Customer confirmed", "The customer confirmed completion of booking {ref}."),
    "SETTLEMENT_SETTLED": ("Earnings settled", "Your earnings for booking {ref} have been settled."),
    "PROVIDER_VERIFIED": ("You're verified", "Your provider account is verified. You can now receive jobs."),
    "PROVIDER_REJECTED": ("Verification unsuccessful", "Your provider application was not approved. See notes."),
    "PROVIDER_SUSPENDED": ("Account suspended", "Your provider account is suspended. Contact support."),
    "ADMIN_PROVIDER_PENDING": ("Provider awaiting verification", "{provider} registered and needs review."),
    "ADMIN_REASSIGNMENT_REQUIRED": ("Booking needs a provider", "Booking {ref} needs manual assignment."),
    "ADMIN_COMPLAINT": ("New complaint", "A customer raised an issue on booking {ref}."),
}


@dataclass(frozen=True)
class OutboundMessage:
    user: User
    type: str
    title: str
    body: str


class NotificationSender(Protocol):
    channel: NotificationChannel

    def send(self, message: OutboundMessage) -> None: ...


class SmsSender:
    """Placeholder for an SMS gateway (e.g. Beem, Africa's Talking). Disabled until configured."""

    channel = NotificationChannel.SMS

    def __init__(self, provider: str, api_key: str) -> None:
        self.provider, self.api_key = provider, api_key

    def send(self, message: OutboundMessage) -> None:  # pragma: no cover - requires real gateway
        raise NotImplementedError(f"SMS provider '{self.provider}' integration is not implemented yet")


def _external_senders() -> list[NotificationSender]:
    s = get_settings()
    if s.sms_provider and s.sms_api_key:
        return [SmsSender(s.sms_provider, s.sms_api_key)]
    return []


def notify(
    db: Session,
    user_id: uuid.UUID,
    type_: str,
    booking: Booking | None = None,
    **params: str,
) -> Notification:
    title, body = TEMPLATES[type_]
    if booking is not None:
        params.setdefault("ref", booking.reference)
    try:
        body = body.format(**params)
    except KeyError:
        pass
    notification = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        booking_id=booking.id if booking else None,
        booking_reference=booking.reference if booking else None,
    )
    db.add(notification)
    for sender in _external_senders():
        user = db.get(User, user_id)
        try:
            sender.send(OutboundMessage(user=user, type=type_, title=title, body=body))
        except Exception:  # external channels must never break the business transaction
            log.warning("notification.external_failed", extra={"channel": sender.channel, "type": type_})
    return notification


def notify_admins(db: Session, type_: str, booking: Booking | None = None, **params: str) -> None:
    admin_ids = db.scalars(
        select(User.id).join(Role).where(Role.code == RoleCode.ADMIN, User.is_active.is_(True))
    ).all()
    for admin_id in admin_ids:
        notify(db, admin_id, type_, booking, **params)
