# SafishaCon: implementation progress report

_Date: 2026-10-01 · Status: MVP implemented, running, and verified end to end._

## Summary

All three experiences run against one FastAPI backend and PostgreSQL: the customer web app, the provider portal, and the admin dashboard, plus the Flutter customer app. The full demo journey has been exercised through the real UI in a headless browser:

> customer books → engine assigns the cleaner → cleaner accepts and progresses → customer confirms → cash confirmed → booking closed → review → admin oversight

It was run both on the Vite dev server and on the Dockerized stack, with zero browser console errors.

## What was built

| Area | Status | Notes |
|---|---|---|
| Data model and migrations | ✅ | 24 tables, UUID keys, FKs, CHECK constraints (including enums and the `commission + earning = total` balance), indexes, timestamps. Alembic `0001`, tested with `downgrade base` and `upgrade head`. `alembic check` is clean. |
| Auth and security | ✅ | bcrypt, JWT access tokens, rotating hashed refresh tokens with reuse detection, RBAC dependencies, ownership checks (404 for other users' data), rate-limited auth, CORS, security headers, production config guards. |
| Pricing engine | ✅ | Base + extra rooms + property type + size + add-ons × quantity, in `Decimal` TZS. A snapshot plus line items is stored on each booking. Commission is admin-configurable. |
| Assignment engine | ✅ | Eligibility: active, verified, accepting jobs, service, area, weekly hours, and capacity (assigned jobs plus open offers). Deterministic ranking. Offers with a TTL, background expiry and re-dispatch, escalation to admins, and manual assignment (direct or as an offer). |
| Booking state machine | ✅ | 13 statuses, transitions validated per actor (customer, provider, admin, system), full history with actor and notes, `allowed_actions` returned to clients. |
| Payments | ✅ | Cash fully working: pending, confirmed by the provider or admin, paid, auto-close. Payment status is separate from booking status. A gateway abstraction exists, with digital methods marked "Coming soon". |
| Settlements and earnings | ✅ | A settlement is created on close; admins mark it settled with a reference; providers see an earnings ledger. |
| Reviews and complaints | ✅ | One review per closed or confirmed booking, ratings recalculated, admin moderation. Complaints open a dispute on completed jobs, and admins resolve them. |
| Notifications | ✅ | In-app notifications for all three roles, localized client-side by type. SMS sender abstraction, disabled until configured. |
| Audit and logging | ✅ | Audit log covering provider verification, price, commission and setting changes, assignment, cash, settlement, complaints, moderation and activation. Structured JSON logs with request IDs and redaction. |
| Customer web | ✅ | Landing page, services, how it works, help, login and register, dashboard, five-step booking wizard with live quote and slots, booking tracking and detail, history, reviews, notifications, profile. |
| Provider portal | ✅ | Onboarding (individual or company), verification banners, dashboard, job requests with countdown, active and completed jobs, large mobile action buttons, availability, services and areas, earnings, ratings, profile. |
| Admin dashboard | ✅ | Overview with "needs attention", bookings with filters, booking detail with timeline, assignments, status and payment actions, providers, customers, services and pricing options, areas and cities, payments, settlements, complaints, reviews, audit log, settings. |
| Localization | ✅ | English and Kiswahili on web (react-i18next JSON with a parity test) and mobile (ARB / gen-l10n). Language choice persists and is synced to the user profile. |
| Flutter customer app | ✅ | Login and register, booking flow, live quote and slots, tracking with polling, cleaner card, confirm completion, rating, cancel, history, EN/SW. Uses the same REST API. |
| Docker | ✅ | `db`, `api` (migrations and seed on boot) and `web` (nginx proxying `/api`), all with health checks. |

## Verification results

| Check | Result |
|---|---|
| Backend `pytest` (PostgreSQL) | **53 passed** |
| `ruff check` | clean |
| Web `eslint --max-warnings=0` | clean |
| Web `tsc` | clean |
| Web `vitest` | **18 passed** |
| Web `vite build` | success |
| `flutter analyze` | no issues |
| `flutter test` | **7 passed**, plus the live API integration test passing against the running backend |
| `flutter build web` | success |
| `docker compose build && up` | all services healthy |
| Seed run twice | no duplicates |
| UI end-to-end journey (Playwright, desktop and 390 px mobile) | passed on dev and Docker, with no console errors |

## Design decisions worth knowing

- **The backend decides everything.** Clients never compute prices, eligibility or allowed actions. Booking responses include `allowed_actions`, so web and mobile simply render the buttons they're given.
- **Privacy.** Providers see the area and earnings in an offer, but not the address or the customer's phone until they accept.
- **New providers** get a neutral 4.0 ranking score, so they receive work instead of starving behind rated providers.
- **Brand.** Changing `APP_NAME` renames the whole product (`/api/v1/config` → web wordmark, titles, copy).

## Next steps (suggested)

1. Integrate mobile money (M-Pesa, Tigo Pesa, Airtel Money) through the `PaymentGateway` interface.
2. Add an SMS provider (e.g. Beem, Africa's Talking) through `NotificationSender`.
3. Move rate limiting and offer expiry out of process (Redis and a worker) before scaling horizontally.
4. Store web refresh tokens in httpOnly cookies, and add rescheduling and auto-confirm after N hours.
5. Have the Flutter app read payment availability from `/config`, and add push notifications.
