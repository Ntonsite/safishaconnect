"""Count SQL statements (and response bytes) per endpoint against the load-test database.

    python scripts/count_endpoint_queries.py [CODE_ROOT]

CODE_ROOT defaults to this backend; point it at a git worktree of an older commit to
compare query behaviour before/after a change. Needs the ``safishacon_load`` dataset
(scripts/generate_load_data.py). Read-mostly: only logs in as load-test accounts.
"""

import os
import sys
from datetime import date, timedelta

root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)
os.environ["DATABASE_URL"] = "postgresql+psycopg://safisha:safisha@localhost:5432/safishacon_load"
os.environ["BACKGROUND_JOBS_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "100000"
os.environ["WRITE_RATE_LIMIT_PER_MINUTE"] = "100000"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, text  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

count = {"n": 0}
event.listen(engine, "before_cursor_execute", lambda *a, **k: count.__setitem__("n", count["n"] + 1))

with engine.connect() as c:
    prov_email = c.execute(
        text(
            "select u.email from providers p join users u on u.id=p.user_id join bookings b on b.provider_id=p.id "
            "group by u.email order by count(*) desc limit 1"
        )
    ).scalar()
    cust_email = c.execute(
        text(
            "select u.email from customers cu join users u on u.id=cu.user_id join bookings b on b.customer_id=cu.id "
            "where u.email like '%@load.local' group by u.email order by count(*) desc limit 1"
        )
    ).scalar()
    svc, area = c.execute(text("select s.id, a.id from services s, service_areas a limit 1")).one()

client = TestClient(app)


def login(email, pw):
    r = client.post("/api/v1/auth/login", json={"identifier": email, "password": pw})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


cust = login(cust_email, "Load@2026")
prov = login(prov_email, "Load@2026")
adm = login("admin@safishacon.local", "Safisha@2026")
bid = client.get("/api/v1/bookings", headers=cust).json()[0]["id"]

next_week = date.today() + timedelta(days=7)
probes = [
    (
        "public/availability",
        "GET",
        f"/api/v1/availability?service_id={svc}&area_id={area}&date={next_week}&duration_minutes=180",
        None,
    ),
    ("customer/bookings", "GET", "/api/v1/bookings", cust),
    ("customer/booking-detail", "GET", f"/api/v1/bookings/{bid}", cust),
    ("provider/jobs?active", "GET", "/api/v1/providers/me/jobs?scope=active", prov),
    ("provider/jobs?completed", "GET", "/api/v1/providers/me/jobs?scope=completed", prov),
    ("provider/dashboard", "GET", "/api/v1/providers/me/dashboard", prov),
    ("provider/earnings", "GET", "/api/v1/providers/me/earnings", prov),
    ("admin/stats", "GET", "/api/v1/admin/stats", adm),
    ("admin/bookings", "GET", "/api/v1/admin/bookings", adm),
    ("admin/payments", "GET", "/api/v1/admin/payments", adm),
]
for name, method, url, headers in probes:
    count["n"] = 0
    r = client.request(method, url, headers=headers or {})
    size = len(r.content)
    print(f"{name:<26} status={r.status_code} queries={count['n']:>5} bytes={size:>9,}")
