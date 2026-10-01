"""RBAC and data-ownership boundaries."""

import pytest

API = "/api/v1"

ADMIN_ENDPOINTS = [
    ("get", "/admin/stats"),
    ("get", "/admin/customers"),
    ("get", "/admin/providers"),
    ("get", "/admin/bookings"),
    ("get", "/admin/payments"),
    ("get", "/admin/settlements"),
    ("get", "/admin/complaints"),
    ("get", "/admin/reviews"),
    ("get", "/admin/audit"),
    ("get", "/admin/settings"),
    ("get", "/admin/services"),
]


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoints_require_admin(client, world, method, path):
    _, customer_h = world.customer()
    _, provider_h = world.provider()
    _, admin_h = world.admin()
    assert getattr(client, method)(API + path).status_code == 401
    assert getattr(client, method)(API + path, headers=customer_h).status_code == 403
    assert getattr(client, method)(API + path, headers=provider_h).status_code == 403
    assert getattr(client, method)(API + path, headers=admin_h).status_code == 200


def test_customer_cannot_see_another_customers_booking(client, world):
    world.provider()
    _, alice_h = world.customer("Alice")
    _, bob_h = world.customer("Bob")
    booking = client.post(f"{API}/bookings", headers=alice_h, json=world.booking_payload()).json()

    assert client.get(f"{API}/bookings/{booking['id']}", headers=bob_h).status_code == 404
    assert client.post(f"{API}/bookings/{booking['id']}/cancel", headers=bob_h, json={}).status_code == 404
    assert client.get(f"{API}/bookings", headers=bob_h).json() == []
    res = client.post(
        f"{API}/complaints",
        headers=bob_h,
        json={"booking_id": booking["id"], "category": "OTHER", "description": "Not my booking at all"},
    )
    assert res.status_code == 404


def test_providers_only_see_their_own_jobs(client, world):
    _, a_h = world.provider("Alpha")
    _, b_h = world.provider("Beta", areas=["Masaki"])
    _, customer_h = world.customer()
    booking = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()
    offer = client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=a_h).json()[0]

    assert client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, headers=b_h).json() == []
    assert client.get(f"{API}/providers/me/jobs/{booking['id']}", headers=b_h).status_code == 404
    assert client.post(f"{API}/assignments/{offer['assignment_id']}/accept", headers=b_h).status_code == 404
    assert client.post(f"{API}/payments/bookings/{booking['id']}/confirm-cash", headers=b_h, json={}).status_code == 404
    res = client.post(f"{API}/providers/me/jobs/{booking['id']}/advance", headers=b_h, json={})
    assert res.status_code == 404


def test_role_specific_endpoints(client, world):
    _, customer_h = world.customer()
    _, provider_h = world.provider()
    assert client.get(f"{API}/providers/me", headers=customer_h).status_code == 403
    assert client.get(f"{API}/bookings", headers=provider_h).status_code == 403
    assert (
        client.post(
            f"{API}/payments/bookings/00000000-0000-0000-0000-000000000000/confirm-cash", headers=customer_h, json={}
        ).status_code
        == 403
    )


def test_customers_cannot_mark_cash_paid(client, world):
    _, cleaner_h = world.provider()
    _, customer_h = world.customer()
    bid = client.post(f"{API}/bookings", headers=customer_h, json=world.booking_payload()).json()["id"]
    assert client.post(f"{API}/payments/bookings/{bid}/confirm-cash", headers=customer_h, json={}).status_code == 403


def test_notifications_are_private(client, world):
    _, alice_h = world.customer("Alice")
    _, bob_h = world.customer("Bob")
    world.provider()
    client.post(f"{API}/bookings", headers=alice_h, json=world.booking_payload())
    alice_notes = client.get(f"{API}/notifications", headers=alice_h).json()
    assert alice_notes["unread"] >= 1
    nid = alice_notes["items"][0]["id"]
    assert client.post(f"{API}/notifications/{nid}/read", headers=bob_h).status_code == 404
    assert client.post(f"{API}/notifications/{nid}/read", headers=alice_h).json()["is_read"] is True


def test_errors_do_not_leak_internals(client):
    res = client.get(f"{API}/bookings/not-a-uuid", headers={"Authorization": "Bearer x"})
    body = res.json()
    assert "error" in body and "Traceback" not in res.text
