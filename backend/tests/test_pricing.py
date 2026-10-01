from decimal import Decimal

from app.services.pricing import split_commission


def quote(client, world, **body):
    service = world.service(body.pop("slug", "deep-cleaning"))
    payload = {"service_id": str(service.id), **body}
    return client.post("/api/v1/quotes", json=payload)


def test_deep_clean_three_bed_two_bath_apartment(client, world):
    service = world.service("deep-cleaning")
    res = quote(
        client, world, property_type_option_id=str(world.option(service, "apartment").id), bedrooms=3, bathrooms=2
    )
    assert res.status_code == 200, res.text
    q = res.json()
    # 70,000 base (1 bed + 1 bath) + 2 × 15,000 bedrooms + 1 × 10,000 bathroom
    assert Decimal(q["base_amount"]) == Decimal(70000)
    assert Decimal(q["adjustments_amount"]) == Decimal(40000)
    assert Decimal(q["total_amount"]) == Decimal(110000)
    assert q["currency"] == "TZS"
    assert q["estimated_duration_minutes"] == 240 + 3 * 45


def test_property_type_and_addons_are_priced(client, world):
    service = world.service("general-home-cleaning")
    fridge = world.option(service, "inside_fridge")
    laundry = world.option(service, "laundry_ironing")
    res = quote(
        client,
        world,
        slug="general-home-cleaning",
        property_type_option_id=str(world.option(service, "standalone_house").id),
        bedrooms=1,
        bathrooms=1,
        addons=[{"option_id": str(fridge.id)}, {"option_id": str(laundry.id), "quantity": 2}],
    )
    q = res.json()
    # 35,000 + house 5,000 + fridge 8,000 + 2 × laundry 7,000
    assert Decimal(q["total_amount"]) == Decimal(62000)
    kinds = [line["kind"] for line in q["lines"]]
    assert kinds == ["BASE", "PROPERTY_TYPE", "ADDON", "ADDON"]


def test_size_based_service(client, world):
    service = world.service("office-cleaning")
    res = quote(client, world, slug="office-cleaning", size_option_id=str(world.option(service, "medium").id))
    assert Decimal(res.json()["total_amount"]) == Decimal(100000)
    missing = quote(client, world, slug="office-cleaning")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "SIZE_REQUIRED"


def test_invalid_options_rejected(client, world):
    deep = world.service("deep-cleaning")
    office = world.service("office-cleaning")
    # Option from another service
    res = quote(client, world, property_type_option_id=str(world.option(office, "small").id), bedrooms=1, bathrooms=1)
    assert res.json()["error"]["code"] == "INVALID_OPTION"
    # Property type required for room-based services
    res = quote(client, world, bedrooms=1, bathrooms=1)
    assert res.json()["error"]["code"] == "PROPERTY_TYPE_REQUIRED"
    # Add-on quantity above maximum
    res = quote(
        client,
        world,
        property_type_option_id=str(world.option(deep, "apartment").id),
        bedrooms=1,
        bathrooms=1,
        addons=[{"option_id": str(world.option(deep, "inside_fridge").id), "quantity": 3}],
    )
    assert res.json()["error"]["code"] == "ADDON_QUANTITY"


def test_commission_split_uses_decimal_whole_shillings():
    econ = split_commission(Decimal(50000), Decimal(20))
    assert (econ.commission_amount, econ.provider_earning) == (Decimal(10000), Decimal(40000))
    econ = split_commission(Decimal(43333), Decimal("17.5"))
    assert econ.commission_amount == Decimal(7583)  # 7583.275 rounds half-up to whole TZS
    assert econ.commission_amount + econ.provider_earning == Decimal(43333)


def test_booking_snapshot_survives_price_and_commission_changes(client, world):
    world.provider()
    _, customer_headers = world.customer()
    _, admin_headers = world.admin()
    booking = client.post("/api/v1/bookings", headers=customer_headers, json=world.booking_payload()).json()
    assert Decimal(booking["total_amount"]) == Decimal(110000)

    service = world.service("deep-cleaning")
    assert (
        client.patch(
            f"/api/v1/admin/services/{service.id}", headers=admin_headers, json={"base_price": "90000"}
        ).status_code
        == 200
    )
    assert (
        client.put("/api/v1/admin/settings/commission_percent", headers=admin_headers, json={"value": "25"}).status_code
        == 200
    )

    detail = client.get(f"/api/v1/admin/bookings/{booking['id']}", headers=admin_headers).json()
    assert Decimal(detail["total_amount"]) == Decimal(110000)
    assert Decimal(detail["commission_percent"]) == Decimal(20)
    assert Decimal(detail["commission_amount"]) == Decimal(22000)
    assert Decimal(detail["provider_earning"]) == Decimal(88000)

    # New bookings use the new configuration.
    new = client.post("/api/v1/bookings", headers=customer_headers, json=world.booking_payload(days=2)).json()
    new_detail = client.get(f"/api/v1/admin/bookings/{new['id']}", headers=admin_headers).json()
    assert Decimal(new_detail["total_amount"]) == Decimal(130000)
    assert Decimal(new_detail["commission_amount"]) == Decimal(32500)

    audit = client.get("/api/v1/admin/audit", headers=admin_headers).json()["items"]
    actions = {a["action"] for a in audit}
    assert {"ADMIN_CHANGED_SERVICE_PRICE", "ADMIN_CHANGED_COMMISSION"} <= actions
