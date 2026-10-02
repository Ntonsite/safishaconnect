"""Concurrency and idempotency guarantees.

Two styles of test:

* **Interleaving tests** run operation A in one database session and *hold its
  transaction open* while operation B runs in a second session on another thread.
  This reproduces the exact race window deterministically instead of hoping two
  threads collide.
* **Burst tests** fire identical HTTP requests in parallel at a real uvicorn server
  (double-clicks, mobile retries, proxy retries).

Every test finishes by checking marketplace-wide invariants.
"""

import threading
import time as _time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import httpx
import pytest
import uvicorn
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    Booking,
    BookingStatusHistory,
    Payment,
    Provider,
    ProviderAssignment,
    ProviderSettlement,
    User,
)
from app.models.enums import (
    ACTIVE_ASSIGNED_STATUSES,
    AssignmentStatus,
    BookingStatus,
    PaymentStatus,
)
from app.services import assignment as assignment_service
from app.services import bookings as booking_service
from app.services import payments as payment_service
from app.services.jobs import run_expiry_once
from app.services.lifecycle import Actor
from app.utils.clock import utcnow

API = "/api/v1"
OPEN = (AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED)


# --------------------------------------------------------------------------- helpers


def outcome(fn: Callable[[], object]) -> str:
    try:
        fn()
        return "ok"
    except AppError as exc:
        return exc.code
    except Exception as exc:  # noqa: BLE001 - surfaced in assertion messages
        return type(exc).__name__


def interleave(first: Callable, second: Callable, hold: float = 0.8) -> tuple[str, str]:
    """Run ``first(db)`` and keep its transaction open while ``second(db)`` runs concurrently.

    ``second`` gets ``hold`` seconds to either finish (it was not blocked) or block on a
    lock; then ``first`` commits and ``second`` is allowed to complete.
    """
    result_b: list[str] = []

    def run_second() -> None:
        with SessionLocal() as db_b:

            def body():
                second(db_b)
                db_b.commit()

            result_b.append(outcome(body))
            db_b.rollback()

    with SessionLocal() as db_a:
        result_a = outcome(lambda: first(db_a))
        worker = threading.Thread(target=run_second)
        worker.start()
        worker.join(timeout=hold)
        if result_a == "ok":
            result_a = outcome(db_a.commit)
        else:
            db_a.rollback()
    worker.join(timeout=15)
    assert not worker.is_alive(), "second operation never finished (deadlock?)"
    return result_a, result_b[0]


def assert_invariants() -> None:
    """Marketplace-wide properties that must hold no matter how requests interleave."""
    with SessionLocal() as db:
        # 1. At most one open (offered/accepted) assignment per booking.
        open_counts = db.execute(
            select(ProviderAssignment.booking_id, func.count())
            .where(ProviderAssignment.status.in_(OPEN))
            .group_by(ProviderAssignment.booking_id)
            .having(func.count() > 1)
        ).all()
        assert not open_counts, f"bookings with several open assignments: {open_counts}"

        bookings = db.scalars(select(Booking)).unique().all()
        for b in bookings:
            # 2. An assigned booking is backed by exactly that provider's accepted assignment.
            if b.status in ACTIVE_ASSIGNED_STATUSES:
                accepted = [a for a in b.assignments if a.status == AssignmentStatus.ACCEPTED]
                assert len(accepted) == 1 and accepted[0].provider_id == b.provider_id, b.reference
            # 3. Terminal / unassigned bookings hold no open assignment.
            if b.status in (BookingStatus.CANCELLED, BookingStatus.REASSIGNMENT_REQUIRED):
                assert not [a for a in b.assignments if a.status in OPEN], b.reference
            # 4. Money always balances.
            assert b.commission_amount + b.provider_earning == b.total_amount

        # 5. No provider is booked beyond capacity at any moment. Peak concurrency is reached at
        #    some job's start, so count the jobs running at each start instant.
        def window(b):
            begin = datetime.combine(b.scheduled_date, b.scheduled_start_time)
            return begin, begin + timedelta(minutes=b.estimated_duration_minutes)

        for provider in db.scalars(select(Provider)).unique():
            jobs = [
                window(b) for b in bookings if b.provider_id == provider.id and b.status in ACTIVE_ASSIGNED_STATUSES
            ]
            for begin, _ in jobs:
                running = sum(1 for s, e in jobs if s <= begin < e)
                assert running <= provider.capacity, f"{provider.display_name} overbooked"

        # 6. Status history is an unbroken chain: no transition was lost to a concurrent write.
        for b in bookings:
            chain = [(h.from_status, h.to_status) for h in b.status_history]
            for (_, prev_to), (next_from, _) in zip(chain, chain[1:], strict=False):
                assert next_from == prev_to, f"{b.reference} history broken: {chain}"
            assert not chain or chain[-1][1] == b.status, f"{b.reference} history ends at {chain[-1][1]}"

        # 7. One settlement per booking and only for paid bookings.
        for s in db.scalars(select(ProviderSettlement)).unique():
            assert s.booking.payment.status == PaymentStatus.PAID


def create_booking(client, headers, payload) -> dict:
    res = client.post(f"{API}/bookings", headers=headers, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def open_assignment(db, booking_id) -> ProviderAssignment:
    return db.scalar(
        select(ProviderAssignment).where(
            ProviderAssignment.booking_id == uuid.UUID(str(booking_id)), ProviderAssignment.status.in_(OPEN)
        )
    )


def accept(provider_id, assignment_id):
    def run(db):
        provider = db.get(Provider, provider_id)
        assignment_service.accept_offer(db, provider, assignment_id)

    return run


# --------------------------------------------------------------------------- interleaving tests


def test_provider_cannot_accept_two_overlapping_jobs_concurrently(client, world, db):
    """A capacity-1 cleaner holding two overlapping offers taps "accept" on both at once."""
    cleaner, _ = world.provider("Solo Cleaner")
    _, customer_h = world.customer()
    first = create_booking(client, customer_h, world.booking_payload(start="10:00"))
    second = create_booking(client, customer_h, world.booking_payload(start="11:00"))
    # The second booking found nobody (the cleaner already holds an overlapping offer).
    # Simulate a second offer reaching the same cleaner (e.g. an admin offer sent moments earlier).
    db.add(
        ProviderAssignment(
            booking_id=uuid.UUID(second["id"]),
            provider_id=cleaner.id,
            status=AssignmentStatus.OFFERED,
            offered_at=utcnow(),
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )
    db.execute(
        update(Booking).where(Booking.id == uuid.UUID(second["id"])).values(status=BookingStatus.FINDING_PROVIDER)
    )
    db.add(
        BookingStatusHistory(
            booking_id=uuid.UUID(second["id"]),
            from_status=BookingStatus.REASSIGNMENT_REQUIRED,
            to_status=BookingStatus.FINDING_PROVIDER,
            note="Offered by admin",
            created_at=utcnow(),
        )
    )
    db.commit()
    a1 = open_assignment(db, first["id"]).id
    a2 = open_assignment(db, second["id"]).id

    results = interleave(accept(cleaner.id, a1), accept(cleaner.id, a2))

    assert sorted(results) == ["SCHEDULE_CONFLICT", "ok"], results
    assert_invariants()


def test_offer_accepted_while_expiry_job_runs(client, world, db):
    """The cleaner accepts in the last second while the expiry worker re-dispatches the booking."""
    world.provider("First Choice")
    world.provider("Backup Cleaner")
    _, customer_h = world.customer()
    booking = create_booking(client, customer_h, world.booking_payload())
    offer = open_assignment(db, booking["id"])
    offered_to = offer.provider_id
    offer.expires_at = utcnow() + timedelta(seconds=1)
    db.commit()

    def accept_then_wait(db_a):
        accept(offered_to, offer.id)(db_a)
        _time.sleep(1.3)  # the offer's deadline passes while this transaction is still open

    results = interleave(accept_then_wait, lambda db_b: run_expiry_once(), hold=0.3)

    # Neither side may fail with a deadlock/serialization error: the worker should simply
    # leave a booking that someone is acting on for its next pass.
    assert results == ("ok", "ok"), results
    assert_invariants()
    with SessionLocal() as check:
        b = check.get(Booking, uuid.UUID(booking["id"]))
        assert b.status == BookingStatus.PROVIDER_ASSIGNED and b.provider_id == offered_to


def test_customer_cancel_racing_provider_accept(client, world, db):
    cleaner, _ = world.provider()
    customer, customer_h = world.customer()
    booking = create_booking(client, customer_h, world.booking_payload())
    offer = open_assignment(db, booking["id"])

    def cancel(db_b):
        b = booking_service.get_customer_booking(db_b, db_b.get(type(customer), customer.id), booking["id"])
        booking_service.cancel_booking(db_b, b, b.customer.user, Actor.CUSTOMER, "changed my mind")

    results = interleave(accept(cleaner.id, offer.id), cancel)

    assert results[0] == "ok", results
    assert_invariants()
    with SessionLocal() as check:
        b = check.get(Booking, uuid.UUID(booking["id"]))
        if b.status == BookingStatus.CANCELLED:
            assert all(a.status not in OPEN for a in b.assignments)


def test_settlement_cannot_be_paid_out_twice(client, world, db):
    cleaner, cleaner_h = world.provider()
    _, customer_h = world.customer()
    admin, _ = world.admin()
    booking = create_booking(client, customer_h, world.booking_payload())
    offer = open_assignment(db, booking["id"])
    assert client.post(f"{API}/assignments/{offer.id}/accept", headers=cleaner_h).status_code == 200
    for step in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        res = client.post(
            f"{API}/providers/me/jobs/{booking['id']}/advance", headers=cleaner_h, json={"expected_status": step}
        )
        assert res.status_code == 200, res.text
    assert client.post(f"{API}/bookings/{booking['id']}/confirm-completion", headers=customer_h).status_code == 200
    res = client.post(f"{API}/payments/bookings/{booking['id']}/confirm-cash", headers=cleaner_h, json={})
    assert res.status_code == 200, res.text
    settlement_id = db.scalar(select(ProviderSettlement.id))

    def settle(ref):
        def run(session):
            s = session.get(ProviderSettlement, settlement_id)
            payment_service.settle(session, session.get(User, admin.id), s, ref, None)

        return run

    results = interleave(settle("MPESA-1"), settle("MPESA-2"))

    assert sorted(results) == ["ALREADY_SETTLED", "ok"], results
    with SessionLocal() as check:
        assert check.get(ProviderSettlement, settlement_id).reference == "MPESA-1"
    assert_invariants()


def test_database_rejects_second_open_assignment(client, world, db):
    """Defence in depth: even buggy code cannot leave two open offers on one booking."""
    world.provider("One")
    other, _ = world.provider("Two")
    _, customer_h = world.customer()
    booking = create_booking(client, customer_h, world.booking_payload())
    db.add(
        ProviderAssignment(
            booking_id=uuid.UUID(booking["id"]),
            provider_id=other.id,
            status=AssignmentStatus.OFFERED,
            offered_at=utcnow(),
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# --------------------------------------------------------------------------- burst tests (real HTTP server)


@pytest.fixture
def live_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = _time.monotonic() + 10
    while not server.started:
        assert _time.monotonic() < deadline, "server did not start"
        _time.sleep(0.02)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def burst(n: int, send: Callable[[httpx.Client, int], httpx.Response]) -> list[httpx.Response]:
    barrier = threading.Barrier(n)

    def one(i):
        with httpx.Client(timeout=30) as http:
            barrier.wait()
            return send(http, i)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(one, range(n)))


def test_duplicate_booking_submissions_with_same_idempotency_key(live_server, world, db):
    world.provider()
    _, customer_h = world.customer()
    payload = world.booking_payload()
    headers = {**customer_h, "Idempotency-Key": str(uuid.uuid4())}

    responses = burst(8, lambda http, _: http.post(f"{live_server}{API}/bookings", headers=headers, json=payload))

    assert all(r.status_code in (200, 201) for r in responses), [r.text for r in responses]
    assert len({r.json()["id"] for r in responses}) == 1
    assert db.scalar(select(func.count(Booking.id))) == 1
    assert db.scalar(select(func.count(Payment.id))) == 1
    assert_invariants()


def test_idempotency_key_reused_with_different_payload_is_rejected(client, world):
    world.provider()
    _, customer_h = world.customer()
    headers = {**customer_h, "Idempotency-Key": "Zm9v_YmFy-bG9uZ2tleQ12"}  # Flutter: base64url, 24 chars
    assert client.post(f"{API}/bookings", headers=headers, json=world.booking_payload()).status_code == 201
    res = client.post(f"{API}/bookings", headers=headers, json=world.booking_payload(start="13:00"))
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_double_tapped_accept_is_idempotent(live_server, client, world, db):
    cleaner, cleaner_h = world.provider()
    _, customer_h = world.customer()
    booking = create_booking(client, customer_h, world.booking_payload())
    offer = open_assignment(db, booking["id"])

    responses = burst(
        6, lambda http, _: http.post(f"{live_server}{API}/assignments/{offer.id}/accept", headers=cleaner_h)
    )

    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    assert {r.json()["booking"]["status"] for r in responses} == {"PROVIDER_ASSIGNED"}
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(ProviderAssignment)) == 1
    assert_invariants()


def test_cash_confirmed_twice_records_single_payment(live_server, client, world, db):
    cleaner, cleaner_h = world.provider()
    _, customer_h = world.customer()
    _, admin_h = world.admin()
    booking = create_booking(client, customer_h, world.booking_payload())
    offer = open_assignment(db, booking["id"])
    client.post(f"{API}/assignments/{offer.id}/accept", headers=cleaner_h)
    for step in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        client.post(
            f"{API}/providers/me/jobs/{booking['id']}/advance", headers=cleaner_h, json={"expected_status": step}
        )
    client.post(f"{API}/bookings/{booking['id']}/confirm-completion", headers=customer_h)
    url = f"{live_server}{API}/payments/bookings/{booking['id']}/confirm-cash"

    # The cleaner double-taps while the admin confirms the same cash from the back office.
    responses = burst(6, lambda http, i: http.post(url, headers=cleaner_h if i % 2 else admin_h, json={}))

    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    db.expire_all()
    payment = db.scalar(select(Payment))
    assert payment.status == PaymentStatus.PAID
    assert db.scalar(select(func.count(ProviderSettlement.id))) == 1
    assert db.get(Booking, uuid.UUID(booking["id"])).status == BookingStatus.CLOSED
    assert_invariants()
