"""Production-readiness behaviour: health, metrics, correlation ids, payment callbacks,
notification outbox, domain events and rate limits."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import events
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Booking, Notification, Payment, PaymentGatewayEvent
from app.models.enums import BookingStatus, PaymentMethod, PaymentStatus
from app.services import notifications
from app.services.payments import GatewayCallback, record_gateway_callback

API = "/api/v1"


# --------------------------------------------------------------------------- health & observability


def test_liveness_and_readiness(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json() == {"status": "ok"}
    assert client.get("/health").status_code == 200  # backwards-compatible alias


def test_readiness_reports_unavailable_database(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "_database_ready", lambda: False)
    res = client.get("/health/ready")
    assert res.status_code == 503 and res.json() == {"status": "unavailable"}  # no infrastructure details


def test_request_id_is_generated_echoed_and_sanitised(client):
    generated = client.get(f"{API}/services").headers["X-Request-ID"]
    assert len(generated) == 16
    assert (
        client.get(f"{API}/services", headers={"X-Request-ID": "trace-abc-12345"}).headers["X-Request-ID"]
        == "trace-abc-12345"
    )
    # Unsafe ids (log/header injection) are replaced, never echoed.
    unsafe = client.get(f"{API}/services", headers={"X-Request-ID": "x\r\nSet-Cookie: a=b"})
    assert unsafe.headers["X-Request-ID"] != "x\r\nSet-Cookie: a=b"
    error = client.get(f"{API}/bookings", headers={"X-Request-ID": "trace-err-12345"})
    assert error.json()["error"]["request_id"] == "trace-err-12345"


def test_metrics_endpoint_exposes_route_templates_not_ids(client, world):
    world.provider()
    _, customer_h = world.customer()
    created = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    client.get(f"{API}/bookings/{created['id']}", headers=customer_h)
    body = client.get("/metrics").text
    assert 'route="/api/v1/bookings/{booking_id}"' in body
    assert created["id"] not in body
    assert "safisha_bookings_created_total" in body
    assert "safisha_db_pool_checked_out" in body
    assert 'safisha_open_bookings{status="FINDING_PROVIDER"}' in body


def test_metrics_token_protects_endpoint(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "metrics_token", "s3cret-token")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer s3cret-token"}).status_code == 200


def test_production_config_rejects_unsafe_values(monkeypatch):
    from app.core.config import Settings

    base = {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "x" * 40,
        "DEMO_MODE": "false",
        "CORS_ORIGIN_REGEX": "",
        "CORS_ORIGINS": "https://app.example.co.tz",
        "DATABASE_URL": "postgresql://app:strong@db/safisha",
        "FORWARDED_ALLOW_IPS": "10.0.0.5",
    }
    for key, value in base.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    try:
        assert isinstance(get_settings(), Settings)
        for key, bad in (("FORWARDED_ALLOW_IPS", "*"), ("CORS_ORIGINS", "*"), ("JWT_SECRET", "dev-only" + "x" * 40)):
            monkeypatch.setenv(key, bad)
            get_settings.cache_clear()
            with pytest.raises(RuntimeError):
                get_settings()
            monkeypatch.setenv(key, base[key])
    finally:
        get_settings.cache_clear()


# --------------------------------------------------------------------------- domain events


def test_events_are_delivered_only_after_commit():
    seen: list[str] = []
    monkeypatch_handlers = events._handlers  # noqa: SLF001
    events.subscribe("test.ping", lambda e: seen.append(e.data["n"]))
    with SessionLocal() as db:
        events.publish(db, "test.ping", n="rolled-back")
        db.rollback()
        events.publish(db, "test.ping", n="committed")
        assert seen == []
        db.commit()
    assert seen == ["committed"]
    monkeypatch_handlers.pop("test.ping")


def test_failing_event_subscriber_never_breaks_the_operation(client, world):
    def explode(_):
        raise RuntimeError("analytics down")

    events.subscribe(events.BOOKING_CREATED, explode)
    try:
        world.provider()
        _, customer_h = world.customer()
        res = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload())
        assert res.status_code == 201
    finally:
        events._handlers[events.BOOKING_CREATED].remove(explode)  # noqa: SLF001


# --------------------------------------------------------------------------- payment gateway callbacks


def _digital_booking(client, world, db) -> Booking:
    world.provider()
    _, customer_h = world.customer()
    booking_id = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    booking = db.get(Booking, uuid.UUID(booking_id))
    # Digital payments are "coming soon" in the product; simulate a future mobile-money booking.
    booking.payment_method = PaymentMethod.MOBILE_MONEY
    booking.payment.method = PaymentMethod.MOBILE_MONEY
    booking.payment.gateway = "mobile_money"
    db.commit()
    return booking


def _callback(booking: Booking, **overrides) -> GatewayCallback:
    fields = {
        "gateway": "mobile_money",
        "external_transaction_id": "MP-TXN-0001",
        "status": "SUCCESS",
        "booking_reference": booking.reference,
        "amount": booking.total_amount,
        "currency": "TZS",
        "event_id": "evt-1",
    }
    return GatewayCallback(**(fields | overrides))


def test_duplicate_gateway_callbacks_apply_once(client, world, db):
    booking = _digital_booking(client, world, db)
    outcomes = []
    for _ in range(3):  # the gateway retries the same notification
        with SessionLocal() as s:
            event, is_new = record_gateway_callback(s, _callback(booking))
            s.commit()
            outcomes.append((event.outcome, is_new))
    assert outcomes == [("APPLIED", True), ("APPLIED", False), ("APPLIED", False)]
    db.expire_all()
    payment = db.scalar(select(Payment).where(Payment.booking_id == booking.id))
    assert payment.status == PaymentStatus.PAID and payment.gateway_reference == "MP-TXN-0001"
    assert db.scalar(select(func.count(PaymentGatewayEvent.id))) == 1


def test_gateway_callback_with_wrong_amount_is_recorded_not_applied(client, world, db):
    booking = _digital_booking(client, world, db)
    with SessionLocal() as s:
        event, _ = record_gateway_callback(s, _callback(booking, amount=Decimal("1000.00"), event_id="evt-x"))
        s.commit()
        assert event.outcome == "AMOUNT_MISMATCH"
    db.expire_all()
    assert db.scalar(select(Payment.status).where(Payment.booking_id == booking.id)) == PaymentStatus.PENDING


def test_gateway_callback_for_cash_booking_is_not_payable(client, world, db):
    world.provider()
    _, customer_h = world.customer()
    booking_id = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    booking = db.get(Booking, uuid.UUID(booking_id))
    with SessionLocal() as s:
        event, _ = record_gateway_callback(s, _callback(booking))
        s.commit()
        assert event.outcome == "NOT_PAYABLE"


def test_cash_confirmation_retry_returns_same_result(client, world, db):
    cleaner, cleaner_h = world.provider()
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    offer = client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=cleaner_h).json()[0]
    client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    for step in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        client.post(f"{API}/providers/me/jobs/{bid}/advance", headers=cleaner_h, json={"expected_status": step})
    first = client.post(f"{API}/payments/bookings/{bid}/confirm-cash", headers=cleaner_h, json={})
    again = client.post(f"{API}/payments/bookings/{bid}/confirm-cash", headers=cleaner_h, json={})
    assert first.status_code == again.status_code == 200
    assert first.json()["paid_at"] == again.json()["paid_at"]


# --------------------------------------------------------------------------- notification outbox


class FlakySms:
    channel = "SMS"

    def __init__(self, failures: int) -> None:
        self.failures, self.sent = failures, []

    def send(self, message) -> None:
        if self.failures:
            self.failures -= 1
            raise TimeoutError("gateway timed out")
        self.sent.append(message.type)


def test_notification_outbox_retries_with_backoff(world, db, monkeypatch):
    customer, _ = world.customer()
    monkeypatch.setattr(notifications, "_external_senders", lambda: [FlakySms(0)])
    notifications.notify(db, customer.user_id, "BOOKING_RECEIVED")
    db.commit()
    note = db.scalar(select(Notification).where(Notification.user_id == customer.user_id))
    assert note.delivery_status == "PENDING"  # queued in the same transaction, not sent inline

    flaky = FlakySms(failures=1)
    assert notifications.deliver_due_notifications(db, senders=[flaky]) == 0
    db.refresh(note)
    assert note.delivery_status == "PENDING" and note.delivery_attempts == 1 and "timed out" in note.last_error
    assert note.next_attempt_at > note.created_at  # backed off, not hammered

    note.next_attempt_at = note.created_at  # time passes
    db.commit()
    assert notifications.deliver_due_notifications(db, senders=[flaky]) == 1
    db.refresh(note)
    assert note.delivery_status == "SENT" and flaky.sent == ["BOOKING_RECEIVED"]


def test_notification_outbox_gives_up_after_max_attempts(world, db, monkeypatch):
    customer, _ = world.customer()
    monkeypatch.setattr(notifications, "_external_senders", lambda: [FlakySms(0)])
    notifications.notify(db, customer.user_id, "BOOKING_RECEIVED")
    db.commit()
    note = db.scalar(select(Notification).where(Notification.user_id == customer.user_id))
    always_down = FlakySms(failures=99)
    for _ in range(get_settings().notification_max_attempts):
        note.next_attempt_at = note.created_at
        db.commit()
        notifications.deliver_due_notifications(db, senders=[always_down])
        db.refresh(note)
    assert note.delivery_status == "FAILED"


def test_booking_succeeds_when_sms_gateway_is_down(client, world, monkeypatch):
    monkeypatch.setattr(notifications, "_external_senders", lambda: [FlakySms(failures=99)])
    world.provider()
    _, customer_h = world.customer()
    res = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload())
    assert res.status_code == 201 and res.json()["status"] == BookingStatus.FINDING_PROVIDER


# --------------------------------------------------------------------------- rate limits


def test_booking_creation_is_rate_limited_per_account(client, world, monkeypatch):
    monkeypatch.setattr(get_settings(), "write_rate_limit_per_minute", 2)
    world.provider(capacity=1)
    _, customer_h = world.customer()
    codes = [
        client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(days=d)).status_code
        for d in (1, 2, 3)
    ]
    assert codes == [201, 201, 429]


def test_rate_limiter_memory_is_bounded(monkeypatch):
    from app.security import rate_limit

    clock = iter(range(10**6))
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: float(next(clock)))
    limiter = rate_limit.SlidingWindowLimiter()
    for i in range(3000):  # 3000 distinct one-off clients, each idle after one request
        limiter.hit(f"ip-{i}", limit=5, window_seconds=60.0)
    assert len(limiter) < 1100


def test_audit_log_records_client_ip_and_ignores_spoofed_forwarded_for(client, world, db):
    from app.models import AuditLog

    _, admin_h = world.admin()
    res = client.put(
        f"{API}/admin/settings/commission_percent",
        headers={**admin_h, "X-Forwarded-For": "6.6.6.6"},
        json={"value": "20"},
    )
    assert res.status_code == 200
    ip = db.scalar(select(AuditLog.ip_address).order_by(AuditLog.created_at.desc()))
    assert ip == "testclient"  # the real peer; an untrusted caller's X-Forwarded-For is ignored
