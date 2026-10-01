from tests.conftest import PASSWORD


def register(client, **overrides):
    body = {"full_name": "Asha Hassan", "phone": "0754 123 456", "email": "asha@example.com", "password": "Usafi2026"}
    body.update(overrides)
    return client.post("/api/v1/auth/register", json=body)


def test_customer_registration_returns_tokens_and_normalises_phone(client):
    res = register(client)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["phone"] == "+255754123456"
    assert data["access_token"] and data["refresh_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["customer_id"]


def test_registration_rejects_duplicates_and_weak_input(client):
    assert register(client).status_code == 201
    dup = register(client, email="other@example.com")
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "PHONE_TAKEN"

    weak = register(client, phone="0765000000", email="x@example.com", password="password")
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "VALIDATION_FAILED"

    bad_phone = register(client, phone="12345", email="y@example.com")
    assert bad_phone.status_code == 422


def test_password_is_hashed_never_stored_plain(client, db):
    from sqlalchemy import select

    from app.models import User

    register(client)
    user = db.scalar(select(User).where(User.email == "asha@example.com"))
    assert user.password_hash != "Usafi2026"
    assert user.password_hash.startswith("$2")


def test_login_with_email_or_phone(client, world):
    customer, _ = world.customer("Juma Ally")
    user = customer.user
    for identifier in (user.email, user.phone, "0" + user.phone[4:]):
        res = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": PASSWORD})
        assert res.status_code == 200, (identifier, res.text)

    wrong = client.post("/api/v1/auth/login", json={"identifier": user.email, "password": "nope12345"})
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    unknown = client.post("/api/v1/auth/login", json={"identifier": "ghost@x.com", "password": "nope12345"})
    assert unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_cannot_login(client, world, db):
    customer, headers = world.customer()
    customer.user.is_active = False
    db.commit()
    res = client.post("/api/v1/auth/login", json={"identifier": customer.user.email, "password": PASSWORD})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "ACCOUNT_INACTIVE"
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_refresh_rotation_and_reuse_detection(client):
    tokens = register(client).json()
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    rotated = first.json()["refresh_token"]
    assert rotated != tokens["refresh_token"]

    # Re-using the old token is refused and revokes the newer one too.
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rotated}).status_code == 401


def test_invalid_and_missing_tokens(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_INVALID"


def test_provider_registration_starts_pending(client, world):
    body = {
        "provider_type": "COMPANY",
        "full_name": "Grace Mushi",
        "business_name": "Safi Kabisa Ltd",
        "phone": "0688 000 111",
        "email": "safi@kabisa.co.tz",
        "password": "Kabisa2026",
        "capacity": 2,
        "service_ids": [str(world.service().id)],
        "area_ids": [str(world.area().id)],
        "availability": [{"day_of_week": 1, "start_time": "08:00", "end_time": "17:00"}],
    }
    res = client.post("/api/v1/auth/register/provider", json=body)
    assert res.status_code == 201, res.text
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    profile = client.get("/api/v1/providers/me", headers=headers).json()
    assert profile["verification_status"] == "PENDING"
    assert profile["display_name"] == "Safi Kabisa Ltd"
    assert profile["contact_person"] == "Grace Mushi"
    assert profile["capacity"] == 2
    assert len(profile["services"]) == 1 and len(profile["availability"]) == 1


def test_change_password(client, world):
    customer, headers = world.customer()
    res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "NewPass123"},
    )
    assert res.status_code == 401
    res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "NewPass123"},
    )
    assert res.status_code == 200
    login = client.post("/api/v1/auth/login", json={"identifier": customer.user.email, "password": "NewPass123"})
    assert login.status_code == 200
