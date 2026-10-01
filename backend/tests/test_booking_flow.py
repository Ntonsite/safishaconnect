"""End-to-end booking lifecycle through the public HTTP API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models import Booking, Payment, ProviderAssignment, ProviderSettlement
from app.models.enums import VerificationStatus
from app.services.jobs import run_expiry_once

API = "/api/v1"


def offers(client, headers):
    return client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=headers).json()


def advance(client, headers, booking_id, expected):
    return client.post(
        f"{API}/providers/me/jobs/{booking_id}/advance", headers=headers, json={"expected_status": expected}
    )


def test_full_demo_journey(client, world, db):
    cleaner, cleaner_h = world.provider("Rehema Juma")
    customer, customer_h = world.customer("Neema Mwakyusa")
    _, admin_h = world.admin()

    # Customer books a deep clean for tomorrow 10:00, paying cash.
    res = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload())
    assert res.status_code == 201, res.text
    booking = res.json()
    bid = booking["id"]
    assert booking["status"] == "FINDING_PROVIDER"
    assert Decimal(booking["total_amount"]) == Decimal(110000)
    assert booking["payment_method"] == "CASH" and booking["payment"]["status"] == "PENDING"
    assert booking["commission_amount"] is None  # economics hidden from customers
    assert "CANCEL" in booking["allowed_actions"]

    # Provider receives the offer (without the exact address yet) and accepts.
    job_offers = offers(client, cleaner_h)
    assert len(job_offers) == 1
    offer = job_offers[0]
    assert offer["booking"]["address_line"] is None
    assert Decimal(offer["booking"]["provider_earning"]) == Decimal(88000)
    assert offer["booking"]["allowed_actions"] == ["ACCEPT", "REJECT"]
    res = client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    assert res.status_code == 200, res.text
    job = res.json()["booking"]
    assert job["status"] == "PROVIDER_ASSIGNED"
    assert job["address_line"] == "Plot 12, Mikocheni B"
    assert job["customer"]["phone"] == customer.user.phone

    # Customer sees the assigned provider.
    view = client.get(f"{API}/bookings/{bid}", headers=customer_h).json()
    assert view["provider"]["display_name"] == "Rehema Juma"
    assert view["provider"]["phone"]

    # Provider progresses the job.
    for expected in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        res = advance(client, cleaner_h, bid, expected)
        assert res.status_code == 200, res.text
        assert res.json()["booking"]["status"] == expected
    assert "CONFIRM_CASH" in res.json()["booking"]["allowed_actions"]

    # Customer confirms completion; booking waits for cash confirmation.
    res = client.post(f"{API}/bookings/{bid}/confirm-completion", headers=customer_h)
    assert res.json()["status"] == "CUSTOMER_CONFIRMED"
    assert "REVIEW" in res.json()["allowed_actions"]

    # Provider confirms cash collected → payment PAID → booking CLOSED.
    res = client.post(f"{API}/payments/bookings/{bid}/confirm-cash", headers=cleaner_h, json={})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "PAID"
    final = client.get(f"{API}/bookings/{bid}", headers=customer_h).json()
    assert final["status"] == "CLOSED"
    assert final["payment"]["paid_at"]

    # Economics persisted.
    settlement = db.scalar(select(ProviderSettlement).where(ProviderSettlement.booking_id == final["id"]))
    assert settlement.provider_earning == Decimal(88000)
    assert settlement.commission_amount == Decimal(22000)
    assert settlement.cash_collected_by_provider is True
    payment = db.scalar(select(Payment).where(Payment.booking_id == settlement.booking_id))
    assert payment.confirmed_by_id == cleaner.user_id

    # Customer reviews; duplicate is refused; provider rating updates.
    res = client.post(f"{API}/reviews", headers=customer_h, json={"booking_id": bid, "rating": 5, "comment": "Superb"})
    assert res.status_code == 201, res.text
    dup = client.post(f"{API}/reviews", headers=customer_h, json={"booking_id": bid, "rating": 4})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_REVIEW"
    profile = client.get(f"{API}/providers/me", headers=cleaner_h).json()
    assert Decimal(profile["rating_average"]) == Decimal(5) and profile["rating_count"] == 1

    # Earnings ledger and admin oversight.
    earnings = client.get(f"{API}/providers/me/earnings", headers=cleaner_h).json()
    assert Decimal(earnings["pending_settlement"]) == Decimal(88000)
    admin_view = client.get(f"{API}/admin/bookings/{bid}", headers=admin_h).json()
    statuses = [h["to_status"] for h in admin_view["history"]]
    assert statuses == [
        "PENDING_CONFIRMATION",
        "CONFIRMED",
        "FINDING_PROVIDER",
        "PROVIDER_ASSIGNED",
        "PROVIDER_EN_ROUTE",
        "PROVIDER_ARRIVED",
        "SERVICE_IN_PROGRESS",
        "COMPLETED_BY_PROVIDER",
        "CUSTOMER_CONFIRMED",
        "CLOSED",
    ]
    assert admin_view["review"]["rating"] == 5
    assert admin_view["assignments"][0]["status"] == "ACCEPTED"

    # Admin settles the provider.
    sid = client.get(f"{API}/admin/settlements", headers=admin_h).json()["items"][0]["id"]
    res = client.post(f"{API}/admin/settlements/{sid}/settle", headers=admin_h, json={"reference": "MPESA-123"})
    assert res.json()["status"] == "SETTLED"
    stats = client.get(f"{API}/admin/stats", headers=admin_h).json()
    assert Decimal(stats["platform_commission"]) == Decimal(22000)
    assert stats["completed_bookings"] == 1


def test_rejection_moves_offer_to_next_provider(client, world, db):
    first, first_h = world.provider("Top Rated")
    second, second_h = world.provider("Second")
    first.rating_average, first.rating_count = Decimal("4.90"), 10
    db.commit()
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]

    assert offers(client, second_h) == []
    offer = offers(client, first_h)[0]
    res = client.post(f"{API}/assignments/{offer['assignment_id']}/reject", headers=first_h, json={"reason": "Busy"})
    assert res.status_code == 200
    assert res.json()["assignment_status"] == "REJECTED"

    second_offer = offers(client, second_h)
    assert len(second_offer) == 1 and second_offer[0]["booking"]["id"] == bid
    # The rejecting provider can no longer act on it.
    again = client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=first_h)
    assert again.status_code == 409


def test_no_eligible_provider_escalates_and_admin_assigns(client, world):
    _, customer_h = world.customer()
    _, admin_h = world.admin()
    # Only provider covers a different area.
    elsewhere, elsewhere_h = world.provider("Masaki Pro", areas=["Masaki"])
    booking = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    assert booking["status"] == "REASSIGNMENT_REQUIRED"

    notes = client.get(f"{API}/notifications", headers=admin_h).json()
    assert any(n["type"] == "ADMIN_REASSIGNMENT_REQUIRED" for n in notes["items"])

    eligible = client.get(f"{API}/admin/bookings/{booking['id']}/eligible-providers", headers=admin_h).json()
    assert eligible == []

    res = client.post(
        f"{API}/admin/bookings/{booking['id']}/assign",
        headers=admin_h,
        json={"provider_id": str(elsewhere.id), "direct": True, "note": "Agreed by phone"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "PROVIDER_ASSIGNED"
    assert res.json()["provider"]["display_name"] == "Masaki Pro"
    active = client.get(f"{API}/providers/me/jobs", params={"scope": "active"}, headers=elsewhere_h).json()
    assert [j["booking"]["id"] for j in active] == [booking["id"]]
    audit = client.get(f"{API}/admin/audit", headers=admin_h).json()["items"]
    assert audit[0]["action"] == "ADMIN_ASSIGNED_BOOKING"


def test_expired_offer_is_reoffered(client, world, db):
    world.provider("Slow")
    _, fast_h = world.provider("Fast")
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    assignment = db.scalar(select(ProviderAssignment).where(ProviderAssignment.booking_id == bid))
    assignment.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    assert run_expiry_once() == 1
    db.expire_all()
    rows = db.scalars(
        select(ProviderAssignment).where(ProviderAssignment.booking_id == bid).order_by(ProviderAssignment.offered_at)
    ).all()
    assert [r.status.value for r in rows] == ["EXPIRED", "OFFERED"]
    assert len(offers(client, fast_h)) + len(offers(client, world.headers(rows[0].provider.user))) == 1


def test_capacity_prevents_double_booking(client, world):
    _, cleaner_h = world.provider("Solo")
    _, customer_h = world.customer()
    first = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    offer = offers(client, cleaner_h)[0]
    client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    # Overlapping second booking: the only provider is busy → escalated.
    second = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(start="12:00")).json()
    assert first["id"] != second["id"]
    assert second["status"] == "REASSIGNMENT_REQUIRED"
    # Non-overlapping slot later the same day is fine (10:00 + 6h15 ends 16:15).
    third = client.post(
        f"{API}/bookings",
        headers=customer_h,
        json=world.booking_payload(slug="general-home-cleaning", start="17:00", bedrooms=1, bathrooms=1),
    ).json()
    assert third["status"] == "FINDING_PROVIDER"


def test_company_capacity_allows_parallel_jobs(client, world):
    from app.models.enums import ProviderType

    _, company_h = world.provider("Team Co", capacity=2, provider_type=ProviderType.COMPANY)
    _, customer_h = world.customer()
    for _ in range(2):
        client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload())
    assert len(offers(client, company_h)) == 2
    third = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    assert third["status"] == "REASSIGNMENT_REQUIRED"


def test_ineligible_providers_never_receive_offers(client, world):
    _, pending_h = world.provider("Pending", status=VerificationStatus.PENDING)
    _, suspended_h = world.provider("Suspended", status=VerificationStatus.SUSPENDED)
    _, wrong_service_h = world.provider("Office only", services=["office-cleaning"])
    _, wrong_hours_h = world.provider("Early bird", end=__import__("datetime").time(12, 0))
    _, customer_h = world.customer()
    booking = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    assert booking["status"] == "REASSIGNMENT_REQUIRED"
    for h in (pending_h, suspended_h, wrong_service_h, wrong_hours_h):
        assert offers(client, h) == []


def test_invalid_transitions_are_rejected(client, world):
    _, cleaner_h = world.provider()
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]

    # Customer cannot confirm completion before the work is done.
    res = client.post(f"{API}/bookings/{bid}/confirm-completion", headers=customer_h)
    assert res.status_code == 409 and res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    offer = offers(client, cleaner_h)[0]
    client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    # Provider cannot skip ahead.
    res = advance(client, cleaner_h, bid, "COMPLETED_BY_PROVIDER")
    assert res.status_code == 409 and res.json()["error"]["code"] == "STALE_STATUS"
    # Cash cannot be confirmed before completion.
    res = client.post(f"{API}/payments/bookings/{bid}/confirm-cash", headers=cleaner_h, json={})
    assert res.status_code == 409 and res.json()["error"]["code"] == "SERVICE_NOT_COMPLETE"
    # Review not possible yet.
    res = client.post(f"{API}/reviews", headers=customer_h, json={"booking_id": bid, "rating": 5})
    assert res.status_code == 422 and res.json()["error"]["code"] == "NOT_REVIEWABLE"
    # Once en route, the customer can no longer cancel.
    advance(client, cleaner_h, bid, "PROVIDER_EN_ROUTE")
    res = client.post(f"{API}/bookings/{bid}/cancel", headers=customer_h, json={})
    assert res.status_code == 409


def test_customer_cancellation_releases_provider(client, world, db):
    _, cleaner_h = world.provider()
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    offer = offers(client, cleaner_h)[0]
    client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    res = client.post(f"{API}/bookings/{bid}/cancel", headers=customer_h, json={"reason": "Travelling"})
    assert res.json()["status"] == "CANCELLED"
    assert res.json()["payment"]["status"] == "CANCELLED"
    a = db.scalar(select(ProviderAssignment).where(ProviderAssignment.booking_id == bid))
    db.refresh(a)
    assert a.status.value == "CANCELLED"
    notes = client.get(f"{API}/notifications", headers=cleaner_h).json()["items"]
    assert notes[0]["type"] == "JOB_CANCELLED"


def test_provider_withdraw_redispatches(client, world):
    _, a_h = world.provider("A")
    _, b_h = world.provider("B")
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    first_h, other_h = (a_h, b_h) if offers(client, a_h) else (b_h, a_h)
    client.post(f"{API}/assignments/{offers(client, first_h)[0]['assignment_id']}/accept", headers=first_h)
    res = client.post(f"{API}/providers/me/jobs/{bid}/withdraw", headers=first_h, json={"reason": "Sick"})
    assert res.status_code == 200, res.text
    assert len(offers(client, other_h)) == 1


def test_complaint_on_completed_job_creates_dispute_and_admin_resolves(client, world):
    _, cleaner_h = world.provider()
    _, customer_h = world.customer()
    _, admin_h = world.admin()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    client.post(f"{API}/assignments/{offers(client, cleaner_h)[0]['assignment_id']}/accept", headers=cleaner_h)
    for s in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        advance(client, cleaner_h, bid, s)

    res = client.post(
        f"{API}/complaints",
        headers=customer_h,
        json={"booking_id": bid, "category": "QUALITY", "description": "Kitchen was not cleaned at all."},
    )
    assert res.status_code == 201, res.text
    assert res.json()["booking_status"] == "DISPUTED"
    dup = client.post(
        f"{API}/complaints",
        headers=customer_h,
        json={"booking_id": bid, "category": "OTHER", "description": "Another issue here please."},
    )
    assert dup.status_code == 409

    cid = client.get(f"{API}/admin/complaints", headers=admin_h).json()["items"][0]["id"]
    res = client.patch(f"{API}/admin/complaints/{cid}", headers=admin_h, json={"status": "RESOLVED"})
    assert res.status_code == 422  # resolution text required
    res = client.patch(
        f"{API}/admin/complaints/{cid}",
        headers=admin_h,
        json={"status": "RESOLVED", "resolution": "Provider returned and re-cleaned the kitchen."},
    )
    assert res.json()["status"] == "RESOLVED"

    # Admin collects cash and closes the dispute.
    res = client.post(f"{API}/admin/bookings/{bid}/payment", headers=admin_h, json={"status": "PAID"})
    assert res.status_code == 200, res.text
    res = client.post(
        f"{API}/admin/bookings/{bid}/status",
        headers=admin_h,
        json={"status": "CUSTOMER_CONFIRMED", "note": "Resolved after re-clean"},
    )
    assert res.json()["status"] == "CLOSED"
    assert res.json()["payment"]["confirmed_by_name"] == "Test Admin"


def test_schedule_validation(client, world):
    world.provider()
    _, customer_h = world.customer()
    past = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(days=-1))
    assert past.json()["error"]["code"] == "TOO_SOON"
    odd = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(start="10:15"))
    assert odd.json()["error"]["code"] == "INVALID_TIME"
    late = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(start="17:00"))
    assert late.json()["error"]["code"] == "INVALID_TIME"  # 6h15 deep clean would end after 22:00
    digital = client.post(
        f"{API}/bookings", headers=customer_h, json=world.booking_payload(payment_method="MOBILE_MONEY")
    )
    assert digital.json()["error"]["code"] == "PAYMENT_METHOD_UNAVAILABLE"


def test_availability_slots_reflect_provider_hours(client, world):
    world.provider(start=__import__("datetime").time(9, 0), end=__import__("datetime").time(17, 0))
    service, area = world.service("general-home-cleaning"), world.area()
    from app.utils.clock import local_today

    day = (local_today() + timedelta(days=1)).isoformat()
    res = client.get(
        f"{API}/availability",
        params={"service_id": str(service.id), "area_id": str(area.id), "date": day, "duration_minutes": 150},
    )
    slots = {s["start_time"][:5]: s["available"] for s in res.json()["slots"]}
    assert slots["08:00"] is False  # before working hours
    assert slots["09:00"] is True
    assert slots["14:00"] is True  # ends 16:30
    assert slots["15:00"] is False  # would end 17:30


def test_pending_booking_confirm_flow(client, world, db):
    world.provider()
    _, customer_h = world.customer()
    res = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload(confirm=False))
    booking = res.json()
    assert booking["status"] == "PENDING_CONFIRMATION"
    assert "CONFIRM" in booking["allowed_actions"]
    res = client.post(f"{API}/bookings/{booking['id']}/confirm", headers=customer_h)
    assert res.json()["status"] == "FINDING_PROVIDER"
    row = db.scalar(select(Booking).where(Booking.id == res.json()["id"]))
    assert row.confirmed_at is not None
