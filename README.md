# SafishaCon

**Book. We assign. We clean.**

SafishaCon is a managed cleaning-services marketplace for Dar es Salaam, Tanzania. Customers choose a service, describe the property, pick a time and pay a fixed price. The platform assigns a verified cleaner or cleaning company, and that provider brings their own equipment and materials. Customers never browse or haggle with cleaners.

> **Want to log in straight away?** See [Demo credentials](#demo-credentials). Every demo account uses the password `Safisha@2026`.

> "SafishaCon" is a working name. The brand is configured in one place (`APP_NAME` and related settings), so the product can be renamed without code changes. See [Brand configuration](#brand-configuration).

---

## Architecture

```
React web app (customer site · provider portal · admin dashboard)
        │  same-origin /api (nginx in Docker, Vite proxy in dev)
        ▼
FastAPI REST API  /api/v1   ← single source of truth for pricing, commission,
        │                     eligibility, booking state machine, payments, RBAC
        ▼
PostgreSQL 16 (SQLAlchemy 2 + Alembic migrations) ◄── worker (offer expiry, notification outbox)

Flutter customer app ──► the same FastAPI REST API (no separate mobile backend)
```

It's a **modular monolith**: one API, one worker and one PostgreSQL database. PostgreSQL row locks, version columns and constraints protect assignment and money flows. There is deliberately no Redis, Kafka or HAProxy yet; see [docs/PRODUCTION_ARCHITECTURE.md](docs/PRODUCTION_ARCHITECTURE.md) and the decision records in [docs/architecture/](docs/architecture/).

| Component | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PyJWT, bcrypt, psycopg 3 |
| Database | PostgreSQL 16 |
| Web | React 18, TypeScript, Vite, React Router, TanStack Query, react-hook-form + zod, react-i18next |
| Mobile | Flutter 3 / Dart 3, provider, http, flutter_secure_storage, gen-l10n (ARB) |
| Infra | Docker Compose (db, api, worker, web) with health checks; nginx serves the web build and proxies `/api` |

---

## Quick start (Docker): the recommended path

Prerequisite: Docker Desktop (or Docker Engine with the Compose v2 plugin).

```bash
cp .env.example .env          # optional: defaults work for local review
docker compose up -d --build
```

On startup the `api` container runs `alembic upgrade head` and then the idempotent seed, so the platform is usable immediately. The `worker` container then starts. It expires unanswered job offers, re-dispatches them, and delivers queued SMS/push notifications.

| What | URL |
|---|---|
| Web app (customer, provider, admin) | http://localhost:8080 |
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Liveness / readiness | http://localhost:8000/health/live · http://localhost:8000/health/ready |
| Prometheus metrics | http://localhost:8000/metrics |

Stop with `docker compose down`. Add `-v` to also delete the database volume.

## Demo credentials

The seed creates these accounts automatically (by Docker on startup, or by `python -m app.seed`). Sign in at **http://localhost:8080/login** (Docker) or **http://localhost:5173/login** (dev server) using either the email or the phone number. In demo mode the login page also offers one-tap demo logins.

| Role | Email | Phone | Password | Lands on | Notes |
|---|---|---|---|---|---|
| Platform admin | `admin@safishacon.local` | `0700 000 001` | `Safisha@2026` | `/admin` | "Safisha Admin" |
| Customer | `customer@safishacon.local` | `0712 000 001` | `Safisha@2026` | `/app` | Neema Mwakyusa, default area Mikocheni. Also works in the Flutter app |
| Individual cleaner (verified) | `cleaner@safishacon.local` | `0713 000 002` | `Safisha@2026` | `/provider` | Rehema Juma, Mon–Sat 08:00–18:00. Portal opens in Kiswahili |
| Cleaning company (verified) | `provider@safishacon.local` | `0714 000 003` | `Safisha@2026` | `/provider` | Usafi Bora Cleaning Services Ltd (contact Joseph Kimaro), 3 parallel teams, all areas |
| Provider awaiting verification | `pending@safishacon.local` | `0715 000 004` | `Safisha@2026` | `/provider` | Baraka Said. Use it to try approval as admin |

The shared password comes from `SEED_DEMO_PASSWORD` in `.env`. Change it there before seeding a fresh database to use a different one.

### Local infrastructure credentials

| Service | Value |
|---|---|
| PostgreSQL host / port | `localhost` / `5432` |
| Database (app) | `safishacon` |
| Database (tests) | `safishacon_test` |
| User / password | `safisha` / `safisha` |
| Connection URL | `postgresql+psycopg://safisha:safisha@localhost:5432/safishacon` |

These defaults come from `.env.example` and `docker-compose.yml` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

> ⚠️ All of the above are development/demo credentials only. Production must run with `DEMO_MODE=false` (the API refuses to start otherwise), a real `JWT_SECRET`, and `python -m app.seed --reference-only`.

### Try the full journey

1. Sign in as the **customer** and choose **Book a cleaning → Deep Cleaning**. Pick Apartment, 3 bedrooms, 2 bathrooms (TZS 110,000), area Mikocheni, tomorrow at 10:00, and pay in **Cash**.
2. The booking moves to *Finding a cleaner*. The engine offers it to the best eligible provider. With the seed data that is **Rehema** (cleaner@), because she has the top rating and covers Mikocheni.
3. Sign in as the **cleaner** (works well on a phone). Go to *Job requests → Accept job*, then tap *I'm on my way → I've arrived → Start cleaning → Complete service*.
4. As the **customer**, tap *Confirm job completed*.
5. As the **cleaner**, tap *Confirm cash collected*. Payment becomes **PAID** and the booking **CLOSED**. The TZS 22,000 commission and TZS 88,000 provider earning are recorded.
6. As the **customer**, leave a 5-star review.
7. As the **admin**, the overview, booking timeline, assignment attempts, payment, settlement and audit log show the whole transaction. Mark the settlement as paid under *Settlements*.

---

## Local development (without Docker for the app)

Prerequisites: Python 3.12, Node 20+ (22 recommended), PostgreSQL 16 (or `docker compose up -d db`), and Flutter 3.24+ for mobile.

### Backend

```bash
docker compose up -d db                     # Postgres on localhost:5432 (also creates safishacon_test)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

The API reads `.env` from `backend/` or the repository root. The defaults point at `localhost:5432`.

### Web

```bash
cd web
npm install
npm run dev        # http://localhost:5173, proxies /api to localhost:8000
```

### Flutter customer app

```bash
cd mobile
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
flutter run -d emulator-5554               # Android emulator defaults to http://10.0.2.2:8000
flutter run --dart-define=API_BASE_URL=http://<your-LAN-IP>:8000   # physical device over Wi-Fi
```

**Physical Android phone over USB** (no Wi-Fi or firewall setup): tunnel the phone's `localhost:8000` to the API.

```bash
adb reverse tcp:8000 tcp:8000
flutter run -d <device-id> --release --dart-define=API_BASE_URL=http://localhost:8000
```

**Full customer journey on a device:** this logs in as the demo customer and books a Deep Cleaning (3 bedrooms, 2 bathrooms, Mikocheni, tomorrow 10:00, cash). The demo cleaner's side runs through the real API: accept, en route, arrived, started, completed and cash. The test then confirms, rates and checks history, and saves screenshots to `docs/screenshots/mobile/`.

```bash
flutter drive -d <device-id> --driver=test_driver/integration_test.dart \
  --target=integration_test/customer_journey_test.dart \
  --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=AUDIT_LOCALE=en   # or sw
```

Add `--dart-define=MANUAL_PROVIDER=true` to perform the cleaner steps yourself in the provider web portal.

The app covers sign-in and registration, service selection, property details, location, date and live time slots, a server-calculated price, cash payment, booking status tracking, the assigned cleaner, completion confirmation, rating, booking history, and an EN/SW switch. Providers and admins use the web portal; the mobile app rejects non-customer logins.

> Offline note: by default Flutter web loads its CanvasKit renderer from Google's CDN. On machines without internet access, build with `flutter build web --no-web-resources-cdn`.

---

## Database migrations

```bash
cd backend
alembic upgrade head              # apply all migrations
alembic downgrade -1              # roll back one revision
alembic downgrade base            # roll back everything
alembic revision --autogenerate -m "describe change"   # after editing models
alembic check                     # verify models and migrations are in sync
```

Rollback strategy: every migration has a working `downgrade()`, and the initial migration was tested with a full `downgrade base → upgrade head` round trip. In production, take a database backup before `upgrade`. To roll back, run `alembic downgrade <previous_revision>` and redeploy the previous image.

## Seed data

```bash
python -m app.seed                   # roles, settings, 10 Dar es Salaam areas, 5 services with pricing, demo accounts and bookings
python -m app.seed --reference-only  # production-safe: no demo accounts
```

The seed is idempotent. Every record is looked up by a natural key (email, slug, option code, booking reference), so running it repeatedly never creates duplicates. It also creates a historical closed and reviewed booking (`SC-DEMO01`) and an upcoming assigned booking (`SC-DEMO02`).

---

## Running tests and checks

```bash
# Backend: real PostgreSQL test database (safishacon_test), migrated with Alembic
cd backend && pytest                 # 80 tests, incl. tests/test_concurrency.py (races & idempotency)
ruff check app tests && ruff format --check app tests

# Web
cd web && npm run lint && npm run typecheck && npm test && npm run build

# Flutter
cd mobile && flutter analyze && flutter test        # 48 tests incl. layouts at 320–430 px, font scale up to 2.0, EN/SW
flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=http://localhost:8000   # against a running API
```

Backend tests cover concurrency and idempotency:

- simultaneous accepts;
- accept versus offer expiry;
- cancel versus accept;
- double settlement;
- duplicate booking submissions with an `Idempotency-Key`;
- double-tapped accept;
- duplicate cash confirmations and gateway callbacks.

They also cover health and metrics, the notification outbox retry and backoff, and production config guards.

Functional coverage includes registration, login, refresh-token rotation and reuse detection, RBAC on every admin endpoint, customer and provider data isolation, pricing and commission (including snapshot immutability), provider eligibility (verification, service, area, hours, capacity), assignment, rejection, reassignment, offer expiry, admin manual assignment, booking state-machine guards, cash payment, settlements, reviews (including duplicates), complaints and disputes, and admin catalogue and settings management.

---

### Load and performance testing

The load-test tooling lives in `backend/loadtest/` and `backend/scripts/`. Run it only against a dedicated `*_load` database, never a real environment:

```bash
cd backend
python -m scripts.generate_load_data        # 150k bookings, 30k customers, 300 providers
python -m scripts.explain_hot_queries       # EXPLAIN ANALYZE of the hot queries
python scripts/count_endpoint_queries.py    # SQL statements per endpoint
locust -f loadtest/locustfile.py --host http://localhost:8001 --headless -u 60 -r 6 -t 3m
```

Measured results and the exact environment are in [docs/PERFORMANCE_BASELINE.md](docs/PERFORMANCE_BASELINE.md).

---

## Environment variables

All variables are documented in [`.env.example`](.env.example). The main groups:

| Group | Variables |
|---|---|
| Brand | `APP_NAME`, `APP_TAGLINE`, `SUPPORT_EMAIL`, `SUPPORT_PHONE`, `SUPPORT_WHATSAPP`, `OFFICE_ADDRESS` |
| Locale and money | `DEFAULT_CURRENCY` (TZS), `DEFAULT_LOCALE` (en/sw), `TIMEZONE`, `DEFAULT_COMMISSION_PERCENT` |
| Database | `DATABASE_URL`, `POSTGRES_DB/USER/PASSWORD/PORT`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_STATEMENT_TIMEOUT_MS`, `DB_LOCK_TIMEOUT_MS` … |
| Security | `JWT_SECRET`, `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, `AUTH_RATE_LIMIT_PER_MINUTE`, `WRITE_RATE_LIMIT_PER_MINUTE`, `FORWARDED_ALLOW_IPS` |
| Server | `WEB_CONCURRENCY` (processes per API container, one per vCPU), `GRACEFUL_SHUTDOWN_SECONDS`, `KEEP_ALIVE_SECONDS` |
| Observability | `METRICS_ENABLED`, `METRICS_TOKEN`, `SLOW_REQUEST_MS`, `LOG_LEVEL`, `LOG_JSON` |
| Operations | `ASSIGNMENT_OFFER_TTL_MINUTES`, `MIN_BOOKING_LEAD_HOURS`, `MAX_BOOKING_DAYS_AHEAD`, `BOOKING_SLOT_START_HOUR/END_HOUR`, `BACKGROUND_JOBS_ENABLED`, `WORKER_INTERVAL_SECONDS` |
| Payments | `DIGITAL_PAYMENTS_ENABLED`, `MOBILE_MONEY_PROVIDER`, `MOBILE_MONEY_API_KEY` |
| Notifications | `SMS_PROVIDER`, `SMS_API_KEY`, `NOTIFICATION_MAX_ATTEMPTS`, `EXTERNAL_CONNECT_TIMEOUT_SECONDS`, `EXTERNAL_READ_TIMEOUT_SECONDS` |
| Demo | `DEMO_MODE`, `SEED_DEMO_PASSWORD`, `RUN_SEED` |
| Web / mobile | `VITE_API_BASE_URL`, `VITE_APP_NAME`; Flutter: `--dart-define=API_BASE_URL=…`, `APP_NAME=…` |

Commission, offer response time, booking lead time and booking window are seeded from the environment and then managed by admins under **Settings**. They are stored in the `platform_settings` table and audited.

### Brand configuration

The brand name, tagline, support contacts, currency and default locale come from backend settings and are served to clients by `GET /api/v1/config`. The web app renders the wordmark from that value. To rebrand to, say, "Safisha Connect", set `APP_NAME="Safisha Connect"` (and `VITE_APP_NAME` for the HTML title fallback, `--dart-define=APP_NAME` for Flutter). No component code changes are needed.

---

## Project structure

```
safishacon/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # routers: auth, public catalogue, bookings, providers, assignments,
│   │   │   └── admin/         #   payments, reviews, complaints, notifications, admin/*
│   │   ├── core/              # settings, errors, error handlers, structured logging
│   │   ├── db/                # declarative base, session
│   │   ├── middleware/        # request id, security headers, access logs
│   │   ├── models/            # 24 tables (users, providers, catalogue, bookings, payments, …)
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── security/          # bcrypt, JWT, refresh tokens, RBAC dependencies, rate limiting
│   │   ├── services/          # pricing, lifecycle (state machine), assignment engine, payments,
│   │   │                      #   bookings, notifications, audit, admin ops, background jobs
│   │   ├── utils/             # money (Decimal), clock (EAT), TZ phone normalisation
│   │   ├── seed.py / seed_data.py
│   │   └── main.py
│   ├── alembic/versions/      # migrations
│   └── tests/                 # pytest against PostgreSQL
├── web/src/
│   ├── api/                   # typed client with token refresh + endpoint modules
│   ├── auth/  config/  i18n/locales/{en,sw}.json
│   ├── layouts/               # public site, app shell (sidebar + mobile bottom nav)
│   ├── features/{public,customer,provider,admin,shared}/
│   ├── shared/{components,hooks,utils}/
│   └── styles/                # design tokens + component/layout CSS
├── mobile/lib/
│   ├── core/                  # config, API client, token store, repository
│   ├── models/  state/  l10n/{app_en,app_sw}.arb
│   └── ui/{screens,widgets,theme.dart}
├── infrastructure/postgres/init/   # creates the test database
├── docs/                      # progress / implementation report
├── docker-compose.yml
└── .env.example
```

---

## Current MVP capabilities

- **Customers:** register and sign in with email or phone, get a live server-side quote, see available time slots, book with cash, track the booking live, see the assigned cleaner, confirm completion, rate, report issues (which opens a dispute), cancel while allowed, receive notifications, and manage their profile and language.
- **Providers (mobile-friendly portal):** onboard as an individual or a company, track verification status, set services, areas and weekly hours, toggle availability, accept or reject job requests with a countdown, step through big status buttons, release a job, confirm cash collected, and view earnings and ratings.
- **Admins:** see actionable metrics; verify, reject, suspend or reactivate providers; manage customers; maintain services, pricing options, cities and areas; view all bookings with filters and full timelines and assignment history; manually assign or reassign (directly or as an offer); override status with correct side effects; manage payments, provider settlements, complaints and review moderation; edit platform settings; read the audit log.
- **Marketplace rules (backend only):** a configurable pricing engine with booking-level price and commission snapshots; a deterministic assignment engine (active, verified, service, area, working hours, capacity, ranking); offer TTL with automatic expiry and re-dispatch; an explicit booking state machine with history; booking status and payment status kept separate; settlements created when bookings close.
- **Cross-cutting:** JWT with rotating refresh tokens and reuse detection, RBAC, ownership checks, uniform error codes, structured JSON logs, an audit log, in-app notifications behind a channel abstraction, English and Kiswahili everywhere (web, mobile and notifications), and a responsive layout down to 360 px.

## Deferred features

Not yet built, by design: a native provider app, AI matching, bidding or negotiation, wallets and automated payouts, subscriptions and loyalty, surge pricing, multi-country operations, corporate contracts, company staff management, chat, live GPS tracking, route optimisation, and advanced analytics.

Extension points already exist:

- `PaymentGateway` in `services/payments.py`. Digital methods show as "Coming soon" until a real M-Pesa, Tigo Pesa, Airtel Money or card integration is added.
- `NotificationSender` in `services/notifications.py`. SMS and push are only enabled when configured, and nothing fakes delivery.
- `rank_key` in `services/assignment.py` controls provider ranking.

## Known limitations

- The application rate limiter is per process. nginx adds a shared edge limit on credential endpoints. Move the limiter to Redis when several API containers serve production traffic ([ADR-002](docs/architecture/ADR-002-redis.md)).
- Admin free-text search uses `ILIKE` with sequential scans (about 220 ms at 150k bookings). Trigram indexes are the documented next step.
- The web app keeps the refresh token in `localStorage`; httpOnly cookies are the production hardening step. Mobile uses secure storage.
- Customers can't reschedule (cancel and rebook instead). There's no automatic completion confirmation after N hours (admins can confirm on the customer's behalf).
- Profile image upload isn't implemented, so there's no file storage to secure.
- The Flutter app always offers cash and shows digital methods as "Coming soon". The web app reads payment availability from `/config`.
- Server error messages are in English. Clients translate known error codes and fall back to the server message.

## Production deployment notes

See [docs/PRODUCTION_ARCHITECTURE.md](docs/PRODUCTION_ARCHITECTURE.md) for the recommended pilot topology, sizing and scaling triggers, and [docs/BACKUP_AND_RECOVERY.md](docs/BACKUP_AND_RECOVERY.md) for backups and restore drills.

- Set the following. The API refuses to boot with unsafe values.
  - `ENVIRONMENT=production` and `DEMO_MODE=false`;
  - a strong random `JWT_SECRET`;
  - explicit `CORS_ORIGINS` and an empty `CORS_ORIGIN_REGEX`;
  - `FORWARDED_ALLOW_IPS` set to your proxy's address.
- Expose only nginx. Don't publish the API port, and protect `/metrics` with `METRICS_TOKEN` if it is reachable.
- Run the `worker` service, exactly one or more; it is safe to run several.
- Use a managed PostgreSQL with point-in-time recovery, and seed with `--reference-only`. Migrations run on API start under an advisory lock; at larger scale, run `alembic upgrade head` as a release step.
- Put the API and web behind HTTPS (TLS termination at the load balancer). The API image runs as a non-root user and sends security headers.
- Rotate demo credentials out entirely; create the first admin through a one-off script or the seed with production-safe values.
- Ship JSON logs to your log platform; every line carries `request_id`. Scrape `/metrics`; recommended alerts are in [ADR-006](docs/architecture/ADR-006-observability.md). Also alert on `unhandled_error`, `assignment.no_candidate` and `auth.refresh_reuse_detected`.
