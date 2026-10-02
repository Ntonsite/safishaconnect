# SafishaCon — Backend Performance Baseline

All numbers on this page were measured on 2 October 2026. Before means the code at commit `71751ed`; after means the hardening changes described in [ARCHITECTURE_ASSESSMENT.md](ARCHITECTURE_ASSESSMENT.md). None of the numbers are estimates.

Front-end first-load performance is covered separately in [PERFORMANCE.md](PERFORMANCE.md).

## 1. Environment

| Item | Value |
|---|---|
| Host | Windows 11 laptop running Docker Desktop. The Linux VM has 12 vCPUs and 7.6 GB RAM. |
| API container | `--cpus 2 --memory 1g`, roughly a small 2-vCPU cloud VM. Python 3.12, uvicorn 0.34, FastAPI 0.115, SQLAlchemy 2.0, psycopg 3.2. |
| API processes | **Before:** 1 uvicorn process, the original image. **After:** measured with 1 (`WEB_CONCURRENCY=1`, like-for-like) and 2 (recommended) processes. |
| API replicas | 1 |
| Database | PostgreSQL 16.15 in Docker (unconstrained CPU, defaults: `shared_buffers=128MB`, `max_connections=100`), with `pg_stat_statements` enabled. |
| DB pool | **Before:** SQLAlchemy defaults (5 + 10 overflow, 30 s wait). **After:** 5 + 5 per process, 5 s wait, statement and lock timeouts set. |
| Background jobs | Ran inside the API container during these tests, as originally. |
| Load generator | Locust 2.37.14 on the **same host**. It competes for host CPU, so absolute numbers are conservative. |
| Network | localhost through Docker port forwarding. There is no nginx in the path, so the numbers are API-only. |

### Test dataset (`scripts/generate_load_data.py`, database `safishacon_load`)

| Table | Rows |
|---|---|
| users | 30,300 (30,000 customers, 300 providers, ≈90% verified, 15% companies) |
| bookings | 150,000 spread over 330 days back to 30 days ahead (78% of past bookings closed) |
| booking_status_history | 1,304,325 |
| booking_price_items | 288,288 |
| provider_assignments | 168,678 |
| payments | 150,000 |
| provider_settlements | 107,185 |
| reviews | 53,580 |
| notifications | 427,917 |

That is roughly "Stage B": hundreds of providers, thousands of customers, and about a year of Dar es Salaam growth.

## 2. Workload (`backend/loadtest/locustfile.py`)

The workload is realistic marketplace traffic, not `/health`. Users are weighted as follows:

| User type (weight) | Think time | Tasks |
|---|---|---|
| Public visitor (5) | 1–4 s | config, services, areas, testimonials; price quotes; availability for a date |
| Customer (3) | 1–4 s | log in; my bookings and booking detail; notifications; quote then **create booking** (with `Idempotency-Key`; this writes and dispatches to a provider) |
| Provider (1) | 2–5 s | log in; offers, active and completed jobs, job detail; dashboard; earnings |
| Admin (1) | 2–5 s | log in; dashboard stats; bookings pages, filters and search; booking detail; payments; settlements |

The main run used **60 concurrent users** (spawn rate 6/s) for **3 minutes**. The stress run used 150 users for 2 minutes. Logins use bcrypt with 12 rounds, the production cost. Auth and write rate limits were raised for the load test only, because all virtual users share one IP.

## 3. Results: 60 concurrent users

### Aggregate

| | Before | After, 1 process | After, 2 processes |
|---|---|---|---|
| Requests completed (3 min) | 3,658 | 6,591 | 6,975 |
| Throughput | 20.5 req/s | 36.8 req/s | 39.0 req/s* |
| p50 | 1,100 ms | 110 ms | **48 ms** |
| p95 | 3,900 ms | 820 ms | **390 ms** |
| p99 | 10,000 ms | 1,300 ms | **860 ms** |
| Slowest request | 85,271 ms | 2,425 ms | 2,541 ms |
| Error rate | 0.05% (2) | 0% | 0.03% (2)† |

\* After the fixes, throughput is limited by the users' think time, not the server: 60 users spend most of their time waiting between actions.

† Both errors were client-side `RemoteDisconnected` on reused keep-alive connections; the server logged no errors. The baseline run had the same artifact. The keep-alive timeout has since been raised from 5 s to 15 s.

An intermediate after run, with the locking, N+1 and index fixes but before the per-request settings cache and the admin-payments eager load, measured p50 490 ms, p95 2,000 ms and p99 3,200 ms at 27.9 req/s. That run located the last two hot spots, which are now fixed.

### Key endpoints: p50 / p95 / p99 in ms

| Endpoint | Before | After, 1 process | After, 2 processes |
|---|---|---|---|
| public: services | 980 / 2,600 / 3,900 | 78 / 620 / 960 | 23 / 220 / 540 |
| public: quote | 930 / 2,900 / 4,000 | 100 / 730 / 1,100 | 56 / 250 / 570 |
| public: availability | 3,400 / 5,300 / 7,200 | 180 / 820 / 1,100 | 57 / 370 / 900 |
| customer: my bookings | 1,300 / 3,000 / 4,300 | 170 / 820 / 1,100 | 58 / 420 / 900 |
| customer: booking detail | 1,200 / 3,000 / 4,300 | 170 / 770 / 1,200 | 58 / 380 / 660 |
| customer: **create booking** | 2,200 / 4,200 / 6,200 | 490 / 1,600 / 2,000 | 220 / 1,300 / 2,000 |
| customer: notifications | 960 / 3,200 / 4,100 | 100 / 640 / 900 | 26 / 220 / 440 |
| auth: login (bcrypt) | 830 / 1,800 / 1,800 | 1,000 / 1,500 / 1,500 | 800 / 1,700 / 2,000 |
| provider: offers | 3,500 / 9,700 / 10,000 | 160 / 950 / 1,100 | 33 / 510 / 700 |
| provider: active jobs | 13,000 / 15,000 / 16,000 | 360 / 1,300 / 1,700 | 140 / 850 / 1,300 |
| provider: completed jobs | **85,000** / 85,000 / 85,000 | 380 / 1,200 / 1,500 | 170 / 670 / 1,100 |
| provider: dashboard | 13,000 / 21,000 / 21,000 | 190 / 670 / 1,300 | 66 / 500 / 1,100 |
| provider: earnings | 20,000 / 23,000 / 23,000 | 240 / 1,000 / 1,200 | 230 / 590 / 690 |
| admin: stats | 1,600 / 3,900 / 4,600 | 360 / 1,100 / 1,500 | 160 / 700 / 1,200 |
| admin: bookings page | 1,900 / 4,000 / 5,900 | 220 / 900 / 1,100 | 110 / 690 / 1,400 |
| admin: search | 2,400 / 4,300 / 5,300 | 550 / 1,300 / 1,600 | 380 / 820 / 1,800 |
| admin: payments | 2,300 / 4,600 / 4,600 | 320 / 760 / 760 | 57 / 440 / 680 |

Login is dominated by bcrypt, roughly 250 ms of CPU by design, and did not get faster. That is intended: it is the cost that makes stolen password hashes expensive to crack.

## 4. Database behaviour

### SQL statements per request

Measured on the 150k dataset with the same probe for the old and new code (`scripts/count_endpoint_queries.py`):

| Endpoint | Before: statements | After: statements | Response size (before → after) |
|---|---|---|---|
| public: availability | 54 | 6 | 770 B |
| customer: my bookings | 29 | 5 | 16.8 KB |
| customer: booking detail | 9 | 9 | 2.5 KB |
| provider: active jobs | 381 | 9 | 199 KB → 163 KB (capped at 50) |
| provider: completed jobs | **2,883** | 9 | **1.8 MB → 188 KB** (50 most recent) |
| provider: dashboard | 524 | 10 | 277 B |
| provider: earnings | 518 | 10 | 187 KB → 36 KB (100 most recent rows; totals still lifetime) |
| admin: stats | 11 (four full-table aggregates) | 9 (one aggregate scan) | 613 B |
| admin: bookings | 28 | 5 | 16.4 KB |
| admin: payments | 28 | 5 | 9.4 KB |

During the baseline load run, `pg_stat_statements` showed 19,294 separate payment lookups, the N+1 from booking summaries, against 3,658 HTTP requests. PostgreSQL's total execution time over the whole 3-minute run was only about 35 s. **The database was never the bottleneck. The application was, through query count, unbounded result sets, and Python CPU.**

### Query plans (`scripts/explain_hot_queries.py`, best of 3, warm cache)

| Query | Before | After | Plan change |
|---|---|---|---|
| Offer-expiry scan (worker) | 47.05 ms | **0.04 ms** | Full `expires_at` index → partial index on live offers |
| Admin payments page | 31.61 ms | **0.10 ms** | Sequential scan + sort → backward index scan |
| Admin settlements page | 25.25 ms | **0.18 ms** | Sequential scan + sort → backward index scan |
| Landing testimonials | 10.85 ms | **0.12 ms** | Sequential scan → partial index |
| Notification inbox | 1.41 ms | **0.11 ms** | Bitmap scan + sort → `(user_id, created_at)` |
| Provider capacity check (one day) | 1.08 ms | **0.28 ms** | Two bitmap scans → `(status, scheduled_date)` |
| Admin "finding provider" queue | 0.68 ms | **0.26 ms** | → `(status, scheduled_date)` |
| Admin stats | 75 ms × 4 scans | **44 ms × 1 scan** | Single `GROUP BY` with sums |
| Customer booking history | 0.13 ms | 0.23 ms | Served by the idempotency index's `customer_id` prefix |
| Admin free-text search | 292 ms | 223 ms | Still sequential scans. Deferred, see assessment M1. |

Migration `0002` took **6.6 s** on this dataset (index builds included).

## 5. Saturation (stress) run: 150 users, 2 processes, 2 vCPUs

| Requests | Throughput | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|
| 4,783 | 40.1 req/s | 220 ms | 8,500 ms | 12,000 ms | 10.2% |

- **Where it saturates.** Throughput plateaus at about 40 req/s, the same as the 60-user run. One 2-vCPU container's capacity for this mix is therefore **about 40 req/s**.
- **How it fails.** All errors are **`503 SERVICE_BUSY` with `Retry-After`**: requests that could not get a database connection within the 5 s pool timeout while the CPU was saturated. PostgreSQL CPU stayed around 4%. There were no 500s, no crashes, no invariant violations, and memory stayed under 260 MB.
- **What it means.** Overload now fails fast and predictably, instead of 85-second hangs. More throughput needs more CPU or more replicas, not a bigger pool (see [PRODUCTION_ARCHITECTURE.md](PRODUCTION_ARCHITECTURE.md)).
- **Context.** A pilot in Stage A (10–20 providers) peaks at well under 1 req/s, which leaves more than 40× headroom on a single container.

## 6. Concurrency results (correctness)

`backend/tests/test_concurrency.py` contains 9 tests: deterministic interleavings plus real parallel HTTP bursts.

| Test | Before | After |
|---|---|---|
| Capacity-1 provider accepts two overlapping jobs at once | ✗ both rejected (offers blocked each other) | ✓ exactly one accepted |
| Provider accepts while the expiry job runs | ✗ deadlock in the job | ✓ both succeed; the job skips the busy booking |
| Customer cancels while the provider accepts | ✗ lost update (history broken) | ✓ consistent |
| Settlement paid out twice | ✗ both "succeeded" | ✓ one paid, one `ALREADY_SETTLED` |
| Database rejects a second open assignment | ✗ accepted | ✓ `IntegrityError` |
| 8 identical bookings with the same `Idempotency-Key` | ✗ 8 bookings | ✓ 1 booking, 1 payment |
| `Idempotency-Key` reused with a different payload | ✗ second booking created | ✓ `409 IDEMPOTENCY_KEY_REUSED` |
| Accept tapped 6 times in parallel | ✗ one OK, the rest `409 OFFER_NOT_AVAILABLE` | ✓ 6 × 200, one assignment |
| Cash confirmed 6 times in parallel (provider and admin) | ✗ one OK, the rest `409 PAYMENT_ALREADY_PROCESSED` | ✓ 6 × 200, 1 payment, 1 settlement |

Before: 0/9 pass. After: 9/9 pass, stable over 6 consecutive runs.

The load runs created 741 bookings and 549 offers concurrently. Audited afterwards: 0 bookings with more than one open assignment, 0 broken history chains, and 0 instants of provider over-capacity.

## 7. Reproducing

```bash
# 1. a disposable database (name must end in _load)
docker exec safishacon-db-1 psql -U safisha -d postgres -c "CREATE DATABASE safishacon_load OWNER safisha"
cd backend
export DATABASE_URL=postgresql+psycopg://safisha:safisha@localhost:5432/safishacon_load
alembic upgrade head && python -m app.seed
python -m scripts.generate_load_data          # ~3 min, 1.5M rows
python -m scripts.explain_hot_queries         # query plans

# 2. an API container with the pilot's resources
docker build -t safishacon-api:load .
docker run -d --name api-load --network safishacon_backend -p 8001:8000 --cpus 2 --memory 1g \
  -e DATABASE_URL=postgresql+psycopg://safisha:safisha@db:5432/safishacon_load \
  -e WEB_CONCURRENCY=2 -e LOG_LEVEL=WARNING \
  -e AUTH_RATE_LIMIT_PER_MINUTE=100000 -e WRITE_RATE_LIMIT_PER_MINUTE=100000 safishacon-api:load

# 3. load (pip install locust)
locust -f loadtest/locustfile.py --host http://localhost:8001 --headless -u 60 -r 6 -t 3m --csv results/run
```

Never point the load test or the generator at a real environment. The generator refuses any database whose name doesn't end in `_load`.
