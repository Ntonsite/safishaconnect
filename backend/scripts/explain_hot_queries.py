"""EXPLAIN ANALYZE the hot SafishaCon queries against a (load-test) database.

    DATABASE_URL=postgresql+psycopg://safisha:safisha@localhost:5432/safishacon_load \
        python -m scripts.explain_hot_queries

Prints execution time, the top plan node and whether an index or a sequential scan was
used. Read-only (every statement runs inside a rolled-back transaction).
"""

import re

import psycopg

from app.core.config import get_settings

QUERIES = {
    "customer booking history": """
        SELECT * FROM bookings WHERE customer_id = %(customer)s
        ORDER BY scheduled_date DESC, scheduled_start_time DESC LIMIT 50""",
    "provider active jobs": """
        SELECT pa.* FROM provider_assignments pa JOIN bookings b ON b.id = pa.booking_id
        WHERE pa.provider_id = %(provider)s AND pa.status = 'ACCEPTED' AND b.provider_id = %(provider)s
          AND b.status IN ('PROVIDER_ASSIGNED','PROVIDER_EN_ROUTE','PROVIDER_ARRIVED','SERVICE_IN_PROGRESS',
                           'COMPLETED_BY_PROVIDER','DISPUTED')
        ORDER BY b.scheduled_date, b.scheduled_start_time LIMIT 50""",
    "provider capacity check (one day)": """
        SELECT provider_id, scheduled_start_time, estimated_duration_minutes FROM bookings
        WHERE provider_id = ANY(%(providers)s) AND scheduled_date = current_date + 3
          AND status IN ('PROVIDER_ASSIGNED','PROVIDER_EN_ROUTE','PROVIDER_ARRIVED','SERVICE_IN_PROGRESS')""",
    "offer expiry scan (worker)": """
        SELECT id, booking_id FROM provider_assignments
        WHERE status = 'OFFERED' AND expires_at <= now() ORDER BY expires_at LIMIT 200""",
    "admin queue: finding provider": """
        SELECT * FROM bookings WHERE status IN ('FINDING_PROVIDER')
        ORDER BY scheduled_date DESC, scheduled_start_time DESC LIMIT 20""",
    "admin payments page": "SELECT * FROM payments ORDER BY created_at DESC LIMIT 20",
    "admin settlements page": "SELECT * FROM provider_settlements ORDER BY created_at DESC LIMIT 20",
    "admin stats (bookings by status)": """
        SELECT status, count(id), coalesce(sum(total_amount),0), coalesce(sum(commission_amount),0)
        FROM bookings GROUP BY status""",
    "admin search (name/phone/ref)": """
        SELECT count(*) FROM bookings b JOIN customers c ON c.id = b.customer_id JOIN users u ON u.id = c.user_id
        WHERE b.reference ILIKE '%%Mwakyusa%%' OR u.full_name ILIKE '%%Mwakyusa%%' OR u.phone ILIKE '%%Mwakyusa%%'""",
    "notifications inbox": """
        SELECT * FROM notifications WHERE user_id = %(user)s ORDER BY created_at DESC LIMIT 30""",
    "landing testimonials": """
        SELECT * FROM reviews WHERE is_hidden = false ORDER BY created_at DESC LIMIT 6""",
    "provider earnings totals": """
        SELECT status, coalesce(sum(provider_earning),0) FROM provider_settlements
        WHERE provider_id = %(provider)s GROUP BY status""",
}


def main() -> None:
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        params = {
            "customer": conn.execute(
                "SELECT customer_id FROM bookings GROUP BY customer_id ORDER BY count(*) DESC LIMIT 1"
            ).fetchone()[0],
            "provider": conn.execute(
                "SELECT provider_id FROM bookings WHERE provider_id IS NOT NULL "
                "GROUP BY provider_id ORDER BY count(*) DESC LIMIT 1"
            ).fetchone()[0],
            "providers": [r[0] for r in conn.execute("SELECT id FROM providers LIMIT 80").fetchall()],
            "user": conn.execute(
                "SELECT user_id FROM notifications GROUP BY user_id ORDER BY count(*) DESC LIMIT 1"
            ).fetchone()[0],
        }
        print(f"{'query':<36} {'ms':>9}  plan")
        for name, sql in QUERIES.items():
            timings = []
            for _ in range(3):  # warm cache; report the best of three
                plan = conn.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}", params).fetchall()
                text = "\n".join(r[0] for r in plan)
                timings.append(float(re.search(r"Execution Time: ([\d.]+)", text).group(1)))
                conn.rollback()
            access = sorted(
                set(
                    re.findall(
                        r"(Seq Scan on \w+|Index (?:Only )?Scan(?: Backward)? using \w+|"
                        r"Bitmap Index Scan on \w+)",
                        text,
                    )
                )
            )
            print(f"{name:<36} {min(timings):>9.2f}  {'; '.join(access)}")


if __name__ == "__main__":
    main()
