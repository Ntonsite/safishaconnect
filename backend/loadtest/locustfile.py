"""SafishaCon load test — realistic marketplace traffic, not just /health.

Run ONLY against a local or dedicated load-test environment seeded with
``scripts/generate_load_data.py`` (it creates bookings and logs in as the
``load.*@load.local`` accounts). See docs/PERFORMANCE_BASELINE.md.

    locust -f loadtest/locustfile.py --host http://localhost:8001 \
        --headless -u 60 -r 6 -t 3m --csv results/run

User mix (weights): public visitors 5, customers 3, providers 1, admins 1.
"""

import random
import uuid
from datetime import date, timedelta

from locust import HttpUser, between, events, task

API = "/api/v1"
PASSWORD = "Load@2026"
CUSTOMERS = 30000
PROVIDERS = 300
ADMIN = ("admin@safishacon.local", "Safisha@2026")

catalog: dict = {}


@events.test_start.add_listener
def load_catalog(environment, **_):
    import requests

    catalog["services"] = requests.get(f"{environment.host}{API}/services", timeout=30).json()
    catalog["areas"] = [a["id"] for a in requests.get(f"{environment.host}{API}/areas", timeout=30).json()]


def booking_body(confirm: bool = True) -> dict:
    service = random.choice(catalog["services"])
    body = {
        "service_id": service["id"],
        "area_id": random.choice(catalog["areas"]),
        "address_line": "Plot 7, Load Test Road",
        "scheduled_date": (date.today() + timedelta(days=random.randint(1, 25))).isoformat(),
        "scheduled_start_time": f"{random.randint(7, 14):02d}:{random.choice(['00', '30'])}",
        "payment_method": "CASH",
        "confirm": confirm,
    }
    if service["uses_rooms"]:
        prop = [o for o in service["options"] if o["group"] == "PROPERTY_TYPE"]
        body |= {"bedrooms": random.randint(1, 4), "bathrooms": random.randint(1, 3)}
        if prop:
            body["property_type_option_id"] = random.choice(prop)["id"]
    else:
        sizes = [o for o in service["options"] if o["group"] == "SIZE"]
        if sizes:
            body["size_option_id"] = random.choice(sizes)["id"]
    return body


class SignedIn(HttpUser):
    abstract = True
    identity: tuple[str, str]

    def on_start(self) -> None:
        email, password = self.identity_for()
        res = self.client.post(f"{API}/auth/login", json={"identifier": email, "password": password}, name="auth/login")
        self.client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"

    def identity_for(self) -> tuple[str, str]:
        raise NotImplementedError


class PublicVisitor(HttpUser):
    """Landing page + booking wizard before sign-in."""

    weight = 5
    wait_time = between(1, 4)

    @task(3)
    def browse(self):
        self.client.get(f"{API}/config", name="public/config")
        self.client.get(f"{API}/services", name="public/services")
        self.client.get(f"{API}/areas", name="public/areas")
        self.client.get(f"{API}/reviews/public", name="public/reviews")

    @task(4)
    def quote(self):
        body = booking_body()
        self.client.post(f"{API}/quotes", json=body, name="public/quote")

    @task(2)
    def availability(self):
        body = booking_body()
        self.client.get(
            f"{API}/availability",
            params={
                "service_id": body["service_id"],
                "area_id": body["area_id"],
                "date": body["scheduled_date"],
                "duration_minutes": 180,
            },
            name="public/availability",
        )


class Customer(SignedIn):
    weight = 3
    wait_time = between(1, 4)

    def identity_for(self):
        return f"load.customer{random.randrange(CUSTOMERS)}@load.local", PASSWORD

    @task(5)
    def my_bookings(self):
        res = self.client.get(f"{API}/bookings", name="customer/bookings")
        rows = res.json() if res.ok else []
        if rows:
            self.client.get(f"{API}/bookings/{random.choice(rows)['id']}", name="customer/booking-detail")

    @task(3)
    def notifications(self):
        self.client.get(f"{API}/notifications", name="customer/notifications")

    @task(2)
    def quote_then_book(self):
        body = booking_body()
        self.client.post(f"{API}/quotes", json=body, name="public/quote")
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        with self.client.post(
            f"{API}/bookings", json=body, headers=headers, name="customer/create-booking", catch_response=True
        ) as res:
            # Business rejections (e.g. slot too soon) are valid outcomes, not load-test errors.
            if res.status_code in (201, 200, 422):
                res.success()


class Provider(SignedIn):
    weight = 1
    wait_time = between(2, 5)

    def identity_for(self):
        return f"load.provider{random.randrange(PROVIDERS)}@load.local", PASSWORD

    @task(3)
    def jobs(self):
        self.client.get(f"{API}/providers/me/jobs", params={"scope": "offers"}, name="provider/jobs?offers")
        res = self.client.get(f"{API}/providers/me/jobs", params={"scope": "active"}, name="provider/jobs?active")
        jobs = res.json() if res.ok else []
        if jobs:
            booking_id = random.choice(jobs)["booking"]["id"]
            self.client.get(f"{API}/providers/me/jobs/{booking_id}", name="provider/job-detail")

    @task(1)
    def history(self):
        self.client.get(f"{API}/providers/me/jobs", params={"scope": "completed"}, name="provider/jobs?completed")

    @task(2)
    def dashboard(self):
        self.client.get(f"{API}/providers/me/dashboard", name="provider/dashboard")

    @task(1)
    def earnings(self):
        self.client.get(f"{API}/providers/me/earnings", name="provider/earnings")


class Admin(SignedIn):
    weight = 1
    wait_time = between(2, 5)

    def identity_for(self):
        return ADMIN

    @task(2)
    def dashboard(self):
        self.client.get(f"{API}/admin/stats", name="admin/stats")

    @task(4)
    def bookings(self):
        res = self.client.get(f"{API}/admin/bookings", params={"page": random.randint(1, 20)}, name="admin/bookings")
        items = res.json().get("items", []) if res.ok else []
        if items:
            self.client.get(f"{API}/admin/bookings/{random.choice(items)['id']}", name="admin/booking-detail")

    @task(2)
    def filter_and_search(self):
        self.client.get(
            f"{API}/admin/bookings",
            params={"status": random.choice(["FINDING_PROVIDER", "PROVIDER_ASSIGNED", "CLOSED"])},
            name="admin/bookings?status",
        )
        self.client.get(
            f"{API}/admin/bookings", params={"q": random.choice(["Mwakyusa", "SC-A", "Neema"])}, name="admin/bookings?q"
        )

    @task(1)
    def money(self):
        self.client.get(f"{API}/admin/payments", name="admin/payments")
        self.client.get(f"{API}/admin/settlements", name="admin/settlements")
