"""Notification abstraction.

``notify`` always writes an in-app notification row inside the caller's transaction,
so it is committed (or rolled back) together with the business change.

External channels (SMS, push) never run inside the request. When a sender is
configured the row is also marked ``delivery_status = PENDING`` — a transactional
outbox — and the worker delivers it after commit with timeouts, retries and
exponential backoff. An SMS gateway outage therefore cannot fail, slow down or
roll back a booking. Nothing pretends to send an SMS when no provider exists.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Booking, Notification, Role, User
from app.models.enums import NotificationChannel, RoleCode
from app.utils.clock import utcnow

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
    """Placeholder for an SMS gateway (e.g. Beem, Africa's Talking). Disabled until configured.

    A real implementation must call the gateway with
    ``EXTERNAL_CONNECT_TIMEOUT_SECONDS`` / ``EXTERNAL_READ_TIMEOUT_SECONDS`` and raise on
    failure; the outbox worker handles retries.
    """

    channel = NotificationChannel.SMS

    def __init__(self, provider: str, api_key: str) -> None:
        self.provider, self.api_key = provider, api_key
        settings = get_settings()
        self.timeout = (settings.external_connect_timeout_seconds, settings.external_read_timeout_seconds)

    def send(self, message: OutboundMessage) -> None:  # pragma: no cover - requires real gateway
        raise NotImplementedError(f"SMS provider '{self.provider}' integration is not implemented yet")


def _external_senders() -> list[NotificationSender]:
    s = get_settings()
    if s.sms_provider and s.sms_api_key:
        return [SmsSender(s.sms_provider, s.sms_api_key)]
    return []


PENDING, SENT, FAILED = "PENDING", "SENT", "FAILED"


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
    if _external_senders():
        notification.delivery_status = PENDING
        notification.next_attempt_at = utcnow()
    db.add(notification)
    return notification


def notify_admins(db: Session, type_: str, booking: Booking | None = None, **params: str) -> None:
    admin_ids = db.scalars(
        select(User.id).join(Role).where(Role.code == RoleCode.ADMIN, User.is_active.is_(True))
    ).all()
    for admin_id in admin_ids:
        notify(db, admin_id, type_, booking, **params)


def backoff(attempt: int) -> timedelta:
    """1, 2, 4, 8... minutes, capped at one hour."""
    return timedelta(minutes=min(2 ** (attempt - 1), 60))


def deliver_due_notifications(db: Session, limit: int = 100, senders: list[NotificationSender] | None = None) -> int:
    """Outbox worker step: deliver queued notifications one at a time. Returns how many were sent.

    Each message is claimed with SKIP LOCKED and committed on its own, so a slow gateway
    holds at most one row and parallel workers never send the same message twice.
    """
    senders = _external_senders() if senders is None else senders
    if not senders:
        return 0
    max_attempts = get_settings().notification_max_attempts
    sent = 0
    for _ in range(limit):
        note = db.scalars(
            select(Notification)
            .where(Notification.delivery_status == PENDING, Notification.next_attempt_at <= utcnow())
            .order_by(Notification.next_attempt_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if note is None:
            break
        user = db.get(User, note.user_id)
        try:
            for sender in senders:
                sender.send(OutboundMessage(user=user, type=note.type, title=note.title, body=note.body))
            note.delivery_status = SENT
            note.last_error = None
            sent += 1
        except Exception as exc:  # retried with backoff; never retried forever
            note.delivery_attempts += 1
            note.last_error = f"{type(exc).__name__}: {exc}"[:255]
            if note.delivery_attempts >= max_attempts:
                note.delivery_status = FAILED
                log.error("notification.delivery_failed", extra={"type": note.type, "attempts": note.delivery_attempts})
            else:
                note.next_attempt_at = utcnow() + backoff(note.delivery_attempts)
                log.warning("notification.delivery_retry", extra={"type": note.type, "attempt": note.delivery_attempts})
        db.commit()
    return sent
