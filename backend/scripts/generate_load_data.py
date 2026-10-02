"""Generate a realistic, large SafishaCon dataset for load testing and query-plan work.

NEVER run this against a real environment: it inserts thousands of fake accounts.
It refuses to run unless the database name ends in ``_load``.

    DATABASE_URL=postgresql+psycopg://safisha:safisha@localhost:5432/safishacon_load \
        python -m scripts.generate_load_data --customers 30000 --providers 300 --bookings 150000

The target database must already be migrated and seeded with reference data
(``alembic upgrade head && python -m app.seed``). Rows are written with COPY, so
~1.5M rows take well under a minute. Every load account uses the password
``Load@2026`` and emails ``load.customer{n}@load.local`` / ``load.provider{n}@load.local``.
"""

import argparse
import random
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import psycopg

from app.core.config import get_settings
from app.security.passwords import hash_password

PASSWORD = "Load@2026"
S = {  # booking status codes
    k: k
    for k in (
        "CONFIRMED FINDING_PROVIDER PROVIDER_ASSIGNED PROVIDER_EN_ROUTE COMPLETED_BY_PROVIDER "
        "CUSTOMER_CONFIRMED CLOSED CANCELLED REASSIGNMENT_REQUIRED DISPUTED"
    ).split()
}
PAST_MIX = [("CLOSED", 78), ("CANCELLED", 12), ("CUSTOMER_CONFIRMED", 4), ("COMPLETED_BY_PROVIDER", 3), ("DISPUTED", 3)]
FUTURE_MIX = [("PROVIDER_ASSIGNED", 60), ("FINDING_PROVIDER", 15), ("CANCELLED", 15), ("REASSIGNMENT_REQUIRED", 10)]
CHAIN = [
    None,
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
FIRST = "Amani Baraka Neema Rehema Juma Halima Said Upendo Zawadi Faraja Imani Mussa Asha Hamisi Grace".split()
LAST = "Mwakyusa Kimaro Massawe Mushi Swai Lyimo Mrema Shirima Ngowi Temba Komba Mbwana Salim Haji".split()
REF = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def pick(mix):
    return random.choices([m[0] for m in mix], weights=[m[1] for m in mix])[0]


def chain_to(target: str) -> list[tuple[str | None, str]]:
    if target in CHAIN:
        steps = CHAIN[: CHAIN.index(target) + 1]
    elif target == "DISPUTED":
        steps = [*CHAIN[: CHAIN.index("COMPLETED_BY_PROVIDER") + 1], "DISPUTED"]
    elif target == "CANCELLED":
        steps = [*CHAIN[: CHAIN.index(random.choice(["CONFIRMED", "FINDING_PROVIDER", "PROVIDER_ASSIGNED"])) + 1]]
        steps.append("CANCELLED")
    else:  # REASSIGNMENT_REQUIRED
        steps = [*CHAIN[: CHAIN.index("FINDING_PROVIDER") + 1], "REASSIGNMENT_REQUIRED"]
    return list(zip(steps, steps[1:], strict=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=int, default=30000)
    parser.add_argument("--providers", type=int, default=300)
    parser.add_argument("--bookings", type=int, default=150000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    if not url.rsplit("/", 1)[-1].split("?")[0].endswith("_load"):
        raise SystemExit("Refusing to run: the database name must end in '_load'.")

    with psycopg.connect(url) as conn:
        cur = conn.cursor()
        if cur.execute("SELECT count(*) FROM users WHERE email LIKE '%@load.local'").fetchone()[0]:
            raise SystemExit("Load data already present. Recreate the database to regenerate.")
        roles = dict(cur.execute("SELECT code, id FROM roles").fetchall())
        services = cur.execute("SELECT id, name_en, base_price, base_duration_minutes FROM services").fetchall()
        areas = [r[0] for r in cur.execute("SELECT id FROM service_areas").fetchall()]
        commission = Decimal(
            cur.execute("SELECT value FROM platform_settings WHERE key = 'commission_percent'").fetchone()[0]
        )
        pw = hash_password(PASSWORD)
        now = datetime.now(UTC)
        today = date.today()

        users, customers, providers, prov_services, prov_areas, avail = [], [], [], [], [], []
        for i in range(args.customers):
            uid = uuid.uuid4()
            created = now - timedelta(days=random.randint(0, 400))
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            users.append(
                (uid, f"load.customer{i}@load.local", f"+2556{i:08d}", name, pw, roles["CUSTOMER"], True, "en", created)
            )
            customers.append((uuid.uuid4(), uid, random.choice(areas), f"Plot {i}, {name.split()[1]} Street", created))
        provider_rows = []
        for i in range(args.providers):
            uid, pid = uuid.uuid4(), uuid.uuid4()
            created = now - timedelta(days=random.randint(30, 400))
            company = random.random() < 0.15
            name = f"{random.choice(LAST)} Cleaning Co." if company else f"{random.choice(FIRST)} {random.choice(LAST)}"
            users.append(
                (uid, f"load.provider{i}@load.local", f"+2558{i:08d}", name, pw, roles["PROVIDER"], True, "en", created)
            )
            status = "VERIFIED" if random.random() < 0.9 else random.choice(["PENDING", "SUSPENDED"])
            capacity = random.randint(2, 4) if company else 1
            providers.append(
                (
                    pid,
                    uid,
                    "COMPANY" if company else "INDIVIDUAL",
                    name,
                    "",
                    random.randint(0, 9),
                    status,
                    True,
                    capacity,
                    0,
                    0,
                    created,
                )
            )
            provider_rows.append((pid, uid, capacity, status))
            for s in random.sample(services, random.randint(2, len(services))):
                prov_services.append((pid, s[0]))
            for a in random.sample(areas, random.randint(3, 6)):
                prov_areas.append((pid, a))
            for day in range(1, 7):
                avail.append((uuid.uuid4(), pid, day, time(7), time(19)))
        verified = [p for p in provider_rows if p[3] == "VERIFIED"]

        bookings, items, history, assignments, payments_, settlements, reviews, notes = ([] for _ in range(8))
        customer_ids = [(c[0], c[1]) for c in customers]
        refs: set[str] = set()
        for _ in range(args.bookings):
            bid = uuid.uuid4()
            cust_id, cust_uid = random.choice(customer_ids)
            svc = random.choice(services)
            day = today + timedelta(days=random.randint(-330, 30))
            start = time(random.randint(7, 15), random.choice([0, 30]))
            target = pick(PAST_MIX) if day < today else pick(FUTURE_MIX)
            steps = chain_to(target)
            total = Decimal(svc[2]) + Decimal(random.randint(0, 12) * 5000)
            comm = (total * commission / 100).quantize(Decimal("1"))
            reached_provider = any(to == "PROVIDER_ASSIGNED" for _, to in steps)
            prov = random.choice(verified) if reached_provider else None
            if target == "CANCELLED":
                prov = None
            ref = "SC-" + "".join(random.choice(REF) for _ in range(6))
            while ref in refs:
                ref = "SC-" + "".join(random.choice(REF) for _ in range(6))
            refs.add(ref)
            created = datetime.combine(day, start, tzinfo=UTC) - timedelta(days=random.randint(1, 10))
            bookings.append(
                (
                    bid, ref, cust_id, svc[0], random.choice(areas), prov[0] if prov else None, target,
                    "Plot 1, Load Street", random.randint(1, 4), random.randint(1, 3), day, start, svc[3],
                    "TZS", svc[1], svc[2], total - Decimal(svc[2]), total, commission, comm, total - comm, "CASH",
                    created, created,
                )
            )  # fmt: skip
            items.append((uuid.uuid4(), bid, 0, "BASE", "base", svc[1], svc[1], 1, svc[2], svc[2]))
            if total > svc[2]:
                extra = total - Decimal(svc[2])
                items.append(
                    (uuid.uuid4(), bid, 1, "ROOMS", "rooms", "Extra rooms", "Vyumba vya ziada", 1, extra, extra)
                )
            for n, (frm, to) in enumerate(steps):
                history.append((uuid.uuid4(), bid, frm, to, created + timedelta(minutes=n * 7)))
            if prov:
                if random.random() < 0.3:  # an earlier provider declined
                    other = random.choice(verified)
                    assignments.append(
                        (
                            uuid.uuid4(),
                            bid,
                            other[0],
                            "REJECTED",
                            False,
                            created,
                            created + timedelta(minutes=30),
                            created,
                        )
                    )
                assignments.append(
                    (uuid.uuid4(), bid, prov[0], "ACCEPTED", False, created, created + timedelta(minutes=30), created)
                )
            if target == "FINDING_PROVIDER":
                offer_to = random.choice(verified)
                expires = now + timedelta(minutes=random.randint(5, 30))
                assignments.append((uuid.uuid4(), bid, offer_to[0], "OFFERED", False, now, expires, None))
            paid = target == "CLOSED"
            pay_status = "PAID" if paid else ("CANCELLED" if target == "CANCELLED" else "PENDING")
            payments_.append(
                (uuid.uuid4(), bid, "CASH", pay_status, total, "TZS", "cash", created if paid else None, created)
            )
            if paid and prov:
                settled = random.random() < 0.7
                settlements.append(
                    (uuid.uuid4(), bid, prov[0], total, comm, total - comm, True,
                     "SETTLED" if settled else "PENDING", created if settled else None, created)
                )  # fmt: skip
                if random.random() < 0.5:
                    reviews.append(
                        (uuid.uuid4(), bid, cust_id, prov[0], random.choice([3, 4, 4, 5, 5, 5]), False, created)
                    )
            for kind in ("BOOKING_CONFIRMED", "PROVIDER_ASSIGNED", "BOOKING_CLOSED")[: random.randint(1, 3)]:
                notes.append(
                    (uuid.uuid4(), cust_uid, "IN_APP", kind, kind.title(), f"Booking {ref}", bid, ref, paid, created)
                )
            if prov:
                notes.append(
                    (uuid.uuid4(), prov[1], "IN_APP", "JOB_OFFERED", "New job", f"Job {ref}", bid, ref, True, created)
                )

        def copy(table: str, cols: str, rows: list[tuple]) -> None:
            with cur.copy(f"COPY {table} ({cols}) FROM STDIN") as cp:
                for row in rows:
                    cp.write_row(row)
            print(f"  {table:<26} {len(rows):>9,}")

        print("Writing rows:")
        copy(
            "users",
            "id, email, phone, full_name, password_hash, role_id, is_active, preferred_locale, created_at",
            users,
        )
        copy("customers", "id, user_id, default_area_id, default_address, created_at", customers)
        copy(
            "providers",
            "id, user_id, provider_type, display_name, bio, years_experience, verification_status, is_accepting_jobs, "
            "capacity, rating_average, rating_count, created_at",
            providers,
        )
        copy("provider_services", "provider_id, service_id", prov_services)
        copy("provider_service_areas", "provider_id, area_id", prov_areas)
        copy("provider_availability", "id, provider_id, day_of_week, start_time, end_time", avail)
        copy(
            "bookings",
            "id, reference, customer_id, service_id, area_id, provider_id, status, address_line, bedrooms, "
            "bathrooms, scheduled_date, scheduled_start_time, estimated_duration_minutes, currency, "
            "service_name_snapshot, base_amount, adjustments_amount, total_amount, commission_percent, "
            "commission_amount, provider_earning, payment_method, created_at, updated_at",
            bookings,
        )
        copy(
            "booking_price_items",
            "id, booking_id, position, kind, code, label_en, label_sw, quantity, unit_amount, amount",
            items,
        )
        copy("booking_status_history", "id, booking_id, from_status, to_status, created_at", history)
        copy(
            "provider_assignments",
            "id, booking_id, provider_id, status, is_manual, offered_at, expires_at, responded_at",
            assignments,
        )
        copy("payments", "id, booking_id, method, status, amount, currency, gateway, paid_at, created_at", payments_)
        copy(
            "provider_settlements",
            "id, booking_id, provider_id, gross_amount, commission_amount, provider_earning, "
            "cash_collected_by_provider, status, settled_at, created_at",
            settlements,
        )
        copy("reviews", "id, booking_id, customer_id, provider_id, rating, is_hidden, created_at", reviews)
        copy(
            "notifications",
            "id, user_id, channel, type, title, body, booking_id, booking_reference, is_read, created_at",
            notes,
        )
        cur.execute(
            """UPDATE providers p SET rating_average = r.avg, rating_count = r.n
               FROM (SELECT provider_id, round(avg(rating), 2) avg, count(*) n FROM reviews GROUP BY provider_id) r
               WHERE r.provider_id = p.id"""
        )
        conn.commit()
        conn.autocommit = True
        cur.execute("ANALYZE")
        print("Done. ANALYZE complete.")


if __name__ == "__main__":
    main()
