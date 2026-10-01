from decimal import Decimal

API = "/api/v1"


def test_provider_verification_workflow(client, world):
    from app.models.enums import VerificationStatus

    pending, pending_h = world.provider("Newbie", status=VerificationStatus.PENDING)
    _, customer_h = world.customer()
    _, admin_h = world.admin()

    # Pending provider receives nothing.
    booking = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    assert booking["status"] == "REASSIGNMENT_REQUIRED"

    queue = client.get(f"{API}/admin/providers", params={"verification_status": "PENDING"}, headers=admin_h).json()
    assert [p["display_name"] for p in queue["items"]] == ["Newbie"]

    res = client.post(
        f"{API}/admin/providers/{pending.id}/verification",
        headers=admin_h,
        json={"action": "APPROVE", "notes": "ID checked"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["verification_status"] == "VERIFIED"
    assert res.json()["verification_history"][0]["decision"] == "APPROVED"
    notes = client.get(f"{API}/notifications", headers=pending_h).json()["items"]
    assert notes[0]["type"] == "PROVIDER_VERIFIED"

    # Now an admin can re-dispatch the stuck booking to them.
    res = client.post(
        f"{API}/admin/bookings/{booking['id']}/status", headers=admin_h, json={"status": "FINDING_PROVIDER"}
    )
    assert res.json()["status"] == "FINDING_PROVIDER"
    offers = client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=pending_h).json()
    assert len(offers) == 1

    # Illegal verification moves are refused.
    res = client.post(f"{API}/admin/providers/{pending.id}/verification", headers=admin_h, json={"action": "REJECT"})
    assert res.status_code == 409

    res = client.post(f"{API}/admin/providers/{pending.id}/verification", headers=admin_h, json={"action": "SUSPEND"})
    assert res.json()["verification_status"] == "SUSPENDED"
    actions = [a["action"] for a in client.get(f"{API}/admin/audit", headers=admin_h).json()["items"]]
    assert "ADMIN_APPROVED_PROVIDER" in actions and "ADMIN_SUSPENDED_PROVIDER" in actions


def test_approval_requires_complete_setup(client, world, db):
    from app.models.enums import VerificationStatus

    provider, _ = world.provider("Incomplete", status=VerificationStatus.PENDING)
    provider.areas.clear()
    db.commit()
    _, admin_h = world.admin()
    res = client.post(f"{API}/admin/providers/{provider.id}/verification", headers=admin_h, json={"action": "APPROVE"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "PROVIDER_SETUP_INCOMPLETE"


def test_service_crud_and_options(client, world):
    _, admin_h = world.admin()
    body = {
        "slug": "window-washing",
        "name_en": "Window Washing",
        "name_sw": "Kuosha Madirisha",
        "base_price": "25000",
        "base_duration_minutes": 90,
        "uses_rooms": False,
    }
    res = client.post(f"{API}/admin/services", headers=admin_h, json=body)
    assert res.status_code == 201, res.text
    sid = res.json()["id"]
    assert client.post(f"{API}/admin/services", headers=admin_h, json=body).status_code == 409

    res = client.post(
        f"{API}/admin/services/{sid}/options",
        headers=admin_h,
        json={
            "group": "ADDON",
            "code": "high_windows",
            "name_en": "High windows",
            "name_sw": "Madirisha ya juu",
            "price_amount": "10000",
            "duration_minutes": 30,
        },
    )
    assert res.status_code == 201
    oid = res.json()["id"]

    public = {s["slug"] for s in client.get(f"{API}/services").json()}
    assert "window-washing" in public
    res = client.post(f"{API}/quotes", json={"service_id": sid, "addons": [{"option_id": oid}]})
    assert Decimal(res.json()["total_amount"]) == Decimal(35000)

    client.patch(f"{API}/admin/options/{oid}", headers=admin_h, json={"is_active": False})
    res = client.post(f"{API}/quotes", json={"service_id": sid, "addons": [{"option_id": oid}]})
    assert res.json()["error"]["code"] == "INVALID_OPTION"

    client.patch(f"{API}/admin/services/{sid}", headers=admin_h, json={"is_active": False})
    assert "window-washing" not in {s["slug"] for s in client.get(f"{API}/services").json()}


def test_area_management(client, world):
    _, admin_h = world.admin()
    city_id = client.get(f"{API}/admin/cities", headers=admin_h).json()[0]["id"]
    res = client.post(f"{API}/admin/areas", headers=admin_h, json={"city_id": city_id, "name": "Tegeta"})
    assert res.status_code == 201
    assert res.json()["slug"] == "dar-es-salaam-tegeta"
    area_id = res.json()["id"]
    assert "Tegeta" in [a["name"] for a in client.get(f"{API}/areas").json()]
    client.patch(f"{API}/admin/areas/{area_id}", headers=admin_h, json={"is_active": False})
    assert "Tegeta" not in [a["name"] for a in client.get(f"{API}/areas").json()]


def test_settings_validation(client, world):
    _, admin_h = world.admin()
    assert (
        client.put(f"{API}/admin/settings/commission_percent", headers=admin_h, json={"value": "95"}).status_code == 422
    )
    assert client.put(f"{API}/admin/settings/unknown", headers=admin_h, json={"value": "1"}).status_code == 422
    res = client.put(f"{API}/admin/settings/assignment_offer_ttl_minutes", headers=admin_h, json={"value": "45"})
    assert {s["key"]: s["value"] for s in res.json()}["assignment_offer_ttl_minutes"] == "45"


def test_deactivated_customer_is_locked_out(client, world):
    customer, customer_h = world.customer()
    _, admin_h = world.admin()
    res = client.patch(f"{API}/admin/customers/{customer.id}", headers=admin_h, json={"is_active": False})
    assert res.json()["is_active"] is False
    assert client.get(f"{API}/bookings", headers=customer_h).status_code == 401


def test_review_moderation_updates_rating(client, world, db):
    from sqlalchemy import select

    from app.models import Review

    _, cleaner_h = world.provider()
    _, customer_h = world.customer()
    _, admin_h = world.admin()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    offer = client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=cleaner_h).json()[0]
    client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=cleaner_h)
    for s in ("PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER"):
        client.post(f"{API}/providers/me/jobs/{bid}/advance", headers=cleaner_h, json={"expected_status": s})
    client.post(f"{API}/bookings/{bid}/confirm-completion", headers=customer_h)
    client.post(f"{API}/reviews", headers=customer_h, json={"booking_id": bid, "rating": 2, "comment": "Rude"})
    review = db.scalar(select(Review))
    res = client.patch(
        f"{API}/admin/reviews/{review.id}",
        headers=admin_h,
        json={"is_hidden": True, "moderation_note": "Abusive language"},
    )
    assert res.json()["is_hidden"] is True
    profile = client.get(f"{API}/providers/me", headers=cleaner_h).json()
    assert profile["rating_count"] == 0
