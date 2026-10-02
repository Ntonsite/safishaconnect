"""Payments, booking closure and provider settlements.

Payment gateways implement :class:`PaymentGateway`. Cash is fully supported.
Digital methods are exposed as "coming soon" until a real gateway (e.g. M-Pesa,
Tigo Pesa, Airtel Money, card acquirer) is implemented and configured — the
platform never fakes a successful third-party payment.

Idempotency: confirming an already-paid payment returns it unchanged, and gateway
callbacks are recorded in an append-only ledger with a unique dedupe key, so network
retries, double taps and duplicate callbacks all produce a single financial result.
Callers hold the booking row lock (see :mod:`app.services.locks`).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import events, metrics
from app.core.config import get_settings
from app.core.errors import PaymentStateError, ValidationFailedError
from app.core.logging import get_logger
from app.models import Booking, Payment, PaymentGatewayEvent, ProviderSettlement, User
from app.models.enums import BookingStatus, PaymentMethod, PaymentStatus, RoleCode, SettlementStatus
from app.services import audit
from app.services.lifecycle import Actor, transition
from app.services.locks import lock_booking
from app.services.notifications import notify
from app.utils.clock import utcnow

log = get_logger("payments")


class PaymentGateway(Protocol):
    method: PaymentMethod
    name: str

    def is_available(self) -> bool: ...

    def initiate(self, payment: Payment) -> None:
        """Start collection (e.g. push a mobile-money prompt). Cash needs nothing."""


class CashGateway:
    method = PaymentMethod.CASH
    name = "cash"

    def is_available(self) -> bool:
        return True

    def initiate(self, payment: Payment) -> None:
        return None


class UnconfiguredDigitalGateway:
    """Stands in for a future digital integration. Never available until implemented."""

    def __init__(self, method: PaymentMethod) -> None:
        self.method = method
        self.name = method.value.lower()

    def is_available(self) -> bool:
        return False

    def initiate(self, payment: Payment) -> None:  # pragma: no cover
        raise PaymentStateError("Digital payments are not available yet.", code="PAYMENT_METHOD_UNAVAILABLE")


GATEWAYS: dict[PaymentMethod, PaymentGateway] = {
    PaymentMethod.CASH: CashGateway(),
    PaymentMethod.MOBILE_MONEY: UnconfiguredDigitalGateway(PaymentMethod.MOBILE_MONEY),
    PaymentMethod.CARD: UnconfiguredDigitalGateway(PaymentMethod.CARD),
}


@dataclass(frozen=True)
class MethodAvailability:
    method: PaymentMethod
    available: bool
    status: str  # AVAILABLE | COMING_SOON


def payment_methods() -> list[MethodAvailability]:
    digital_enabled = get_settings().digital_payments_enabled
    out = []
    for method, gw in GATEWAYS.items():
        available = gw.is_available() and (method == PaymentMethod.CASH or digital_enabled)
        out.append(MethodAvailability(method, available, "AVAILABLE" if available else "COMING_SOON"))
    return out


def ensure_method_available(method: PaymentMethod) -> None:
    if not next(m for m in payment_methods() if m.method == method).available:
        raise ValidationFailedError(
            "This payment method is coming soon. Please choose cash.", code="PAYMENT_METHOD_UNAVAILABLE"
        )


def create_payment(db: Session, booking: Booking) -> Payment:
    gateway = GATEWAYS[booking.payment_method]
    payment = Payment(
        booking_id=booking.id,
        method=booking.payment_method,
        status=PaymentStatus.PENDING,
        amount=booking.total_amount,
        currency=booking.currency,
        gateway=gateway.name,
    )
    db.add(payment)
    gateway.initiate(payment)
    return payment


CASH_CONFIRMABLE_BY_PROVIDER = {BookingStatus.COMPLETED_BY_PROVIDER, BookingStatus.CUSTOMER_CONFIRMED}
CASH_CONFIRMABLE_BY_ADMIN = CASH_CONFIRMABLE_BY_PROVIDER | {BookingStatus.DISPUTED, BookingStatus.SERVICE_IN_PROGRESS}


def _reject(code: str, message: str) -> PaymentStateError:
    metrics.PAYMENT_FAILURES.labels(code).inc()
    return PaymentStateError(message, code=code)


def confirm_cash(db: Session, booking: Booking, user: User, note: str | None = None) -> Payment:
    payment = booking.payment
    if payment is None or payment.method != PaymentMethod.CASH:
        raise _reject("PAYMENT_STATE_ERROR", "This booking is not a cash booking.")
    if payment.status == PaymentStatus.PAID:
        # Retry / double tap / provider and admin confirming the same cash: one result, no new side effects.
        return payment
    if payment.status != PaymentStatus.PENDING:
        raise _reject("PAYMENT_ALREADY_PROCESSED", f"Payment is already {payment.status}.")
    allowed = CASH_CONFIRMABLE_BY_ADMIN if user.role_code == RoleCode.ADMIN else CASH_CONFIRMABLE_BY_PROVIDER
    if booking.status not in allowed:
        raise _reject("SERVICE_NOT_COMPLETE", "Cash can only be confirmed once the service is complete.")

    payment.status = PaymentStatus.PAID
    payment.paid_at = utcnow()
    payment.confirmed_by_id = user.id
    payment.notes = note
    notify(db, booking.customer.user_id, "PAYMENT_CONFIRMED", booking)
    if user.role_code == RoleCode.ADMIN:
        audit.record(
            db,
            user,
            "ADMIN_CONFIRMED_CASH_PAYMENT",
            "payment",
            payment.id,
            {"reference": booking.reference, "amount": str(payment.amount)},
        )
    log.info("payment.cash_confirmed", extra={"booking": booking.reference, "by_role": user.role_code})
    events.publish(db, events.PAYMENT_CONFIRMED, booking=booking.reference, method=payment.method.value)
    try_close(db, booking)
    return payment


ADMIN_PAYMENT_TRANSITIONS = {
    (PaymentStatus.PENDING, PaymentStatus.FAILED),
    (PaymentStatus.FAILED, PaymentStatus.PENDING),
    (PaymentStatus.PAID, PaymentStatus.REFUNDED),
}


def admin_set_payment_status(
    db: Session, admin: User, booking: Booking, status: PaymentStatus, note: str | None
) -> Payment:
    payment = booking.payment
    if status == PaymentStatus.PAID:
        return confirm_cash(db, booking, admin, note)
    if (payment.status, status) not in ADMIN_PAYMENT_TRANSITIONS:
        raise PaymentStateError(f"Payment cannot move from {payment.status} to {status}.")
    old = payment.status
    payment.status = status
    payment.notes = note
    audit.record(
        db,
        admin,
        "ADMIN_UPDATED_PAYMENT",
        "payment",
        payment.id,
        {"reference": booking.reference, "from": old, "to": status, "note": note},
    )
    return payment


def try_close(db: Session, booking: Booking) -> bool:
    """Close the booking once the customer has confirmed and the money is in."""
    if booking.status != BookingStatus.CUSTOMER_CONFIRMED or booking.payment.status != PaymentStatus.PAID:
        return False
    transition(db, booking, BookingStatus.CLOSED, Actor.SYSTEM, note="Service confirmed and paid")
    ensure_settlement(db, booking)
    notify(db, booking.customer.user_id, "BOOKING_CLOSED", booking)
    return True


def ensure_settlement(db: Session, booking: Booking) -> ProviderSettlement | None:
    if booking.provider_id is None or booking.payment.status != PaymentStatus.PAID:
        return None
    existing = db.scalar(select(ProviderSettlement).where(ProviderSettlement.booking_id == booking.id))
    if existing:
        return existing
    confirmer = db.get(User, booking.payment.confirmed_by_id) if booking.payment.confirmed_by_id else None
    settlement = ProviderSettlement(
        booking_id=booking.id,
        provider_id=booking.provider_id,
        gross_amount=booking.total_amount,
        commission_amount=booking.commission_amount,
        provider_earning=booking.provider_earning,
        cash_collected_by_provider=bool(
            booking.payment.method == PaymentMethod.CASH and confirmer and confirmer.role_code == RoleCode.PROVIDER
        ),
        status=SettlementStatus.PENDING,
    )
    db.add(settlement)
    return settlement


def settle(db: Session, admin: User, settlement: ProviderSettlement, reference: str | None, note: str | None) -> None:
    # Lock and re-read: two admins (or a double click) must not pay a provider out twice.
    settlement = db.scalars(
        select(ProviderSettlement)
        .where(ProviderSettlement.id == settlement.id)
        .with_for_update(of=ProviderSettlement, key_share=True)
        .execution_options(populate_existing=True)
    ).one()
    if settlement.status == SettlementStatus.SETTLED:
        raise PaymentStateError("This settlement is already settled.", code="ALREADY_SETTLED")
    settlement.status = SettlementStatus.SETTLED
    settlement.settled_at = utcnow()
    settlement.settled_by_id = admin.id
    settlement.reference = reference
    settlement.note = note
    notify(db, settlement.provider.user_id, "SETTLEMENT_SETTLED", settlement.booking)
    audit.record(
        db,
        admin,
        "ADMIN_SETTLED_PROVIDER",
        "settlement",
        settlement.id,
        {"reference": settlement.booking.reference, "amount": str(settlement.provider_earning), "ref": reference},
    )
    events.publish(db, events.SETTLEMENT_SETTLED, booking=settlement.booking.reference)


def cancel_payment(booking: Booking) -> None:
    if booking.payment and booking.payment.status == PaymentStatus.PENDING:
        booking.payment.status = PaymentStatus.CANCELLED


# --------------------------------------------------------------------------- gateway callbacks


@dataclass(frozen=True)
class GatewayCallback:
    """A normalised payment-provider notification (built by each gateway's webhook adapter)."""

    gateway: str
    external_transaction_id: str
    status: str  # SUCCESS | FAILED | PENDING
    booking_reference: str | None
    amount: Decimal | None = None
    currency: str | None = None
    event_id: str | None = None  # the gateway's own callback id, when it provides one
    payload: dict[str, Any] | None = None

    @property
    def dedupe_key(self) -> str:
        return self.event_id or f"{self.external_transaction_id}:{self.status}"


def record_gateway_callback(db: Session, cb: GatewayCallback) -> tuple[PaymentGatewayEvent, bool]:
    """Record and apply a gateway callback exactly once. Returns (event, is_new).

    Safe under retries and concurrent duplicate deliveries: the ledger insert uses
    ``ON CONFLICT DO NOTHING`` on (gateway, dedupe_key), so only the first copy is
    applied; every copy gets the same answer. The caller commits.
    """
    inserted = db.scalar(
        insert(PaymentGatewayEvent)
        .values(
            gateway=cb.gateway,
            dedupe_key=cb.dedupe_key,
            external_transaction_id=cb.external_transaction_id,
            status=cb.status,
            amount=cb.amount,
            currency=cb.currency,
            payload=cb.payload,
            received_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["gateway", "dedupe_key"])
        .returning(PaymentGatewayEvent.id)
    )
    if inserted is None:
        existing = db.scalar(
            select(PaymentGatewayEvent).where(
                PaymentGatewayEvent.gateway == cb.gateway, PaymentGatewayEvent.dedupe_key == cb.dedupe_key
            )
        )
        log.info("payment.gateway_duplicate", extra={"gateway": cb.gateway, "txn": cb.external_transaction_id})
        return existing, False

    event = db.get(PaymentGatewayEvent, inserted)
    event.outcome = _apply_gateway_callback(db, cb, event)
    event.processed_at = utcnow()
    events.publish(db, events.PAYMENT_GATEWAY_EVENT, gateway=cb.gateway, outcome=event.outcome)
    return event, True


def _apply_gateway_callback(db: Session, cb: GatewayCallback, event: PaymentGatewayEvent) -> str:
    booking_id = db.scalar(select(Booking.id).where(Booking.reference == cb.booking_reference))
    if booking_id is None:
        log.error("payment.gateway_unknown_booking", extra={"gateway": cb.gateway, "txn": cb.external_transaction_id})
        return "UNKNOWN_PAYMENT"
    booking = lock_booking(db, booking_id)
    payment = booking.payment
    event.payment_id = payment.id
    if payment.method == PaymentMethod.CASH or GATEWAYS[payment.method].name != cb.gateway:
        log.error("payment.gateway_method_mismatch", extra={"booking": booking.reference, "gateway": cb.gateway})
        return "NOT_PAYABLE"
    if cb.status != "SUCCESS":
        if cb.status == "FAILED" and payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.notes = f"{cb.gateway} reported failure ({cb.external_transaction_id})"
            return "MARKED_FAILED"
        return "RECORDED"
    if payment.status == PaymentStatus.PAID:
        return "ALREADY_APPLIED"
    # The ledger amount must match the immutable booking snapshot exactly; never trust a mismatch.
    if cb.amount is None or cb.amount != payment.amount or (cb.currency or payment.currency) != payment.currency:
        log.error(
            "payment.gateway_amount_mismatch",
            extra={"booking": booking.reference, "expected": str(payment.amount), "got": str(cb.amount)},
        )
        metrics.PAYMENT_FAILURES.labels("AMOUNT_MISMATCH").inc()
        return "AMOUNT_MISMATCH"
    if payment.status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        return "NOT_PAYABLE"
    payment.status = PaymentStatus.PAID
    payment.paid_at = utcnow()
    payment.gateway_reference = cb.external_transaction_id
    notify(db, booking.customer.user_id, "PAYMENT_CONFIRMED", booking)
    events.publish(db, events.PAYMENT_CONFIRMED, booking=booking.reference, method=payment.method.value)
    try_close(db, booking)
    return "APPLIED"
