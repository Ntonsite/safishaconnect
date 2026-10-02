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

---

## UI/UX audit and polish (2026-10-01)

Each journey was run in a real browser (Playwright) as customer, cleaner, cleaning company, pending provider and admin, at 1440, 390 and 320 px and in both languages.

**Problems found and fixed**

| Area | Problem | Fix |
|---|---|---|
| Booking wizard (mobile) | The date strip on the schedule step pushed the page 788 px wider than the screen | Grid children can now shrink (`.detail-grid > * { min-width: 0 }`); overflow re-checked at 320 and 390 px |
| Booking wizard (mobile) | The price was only visible at the very bottom, below the actions | Sticky action bar shows the live total on every step; the review step leads with the full summary |
| Price presentation | Equipment being included wasn't visible in the price | Every price breakdown (web and Flutter) shows "Equipment & materials: Included" |
| Copy | "1 bedrooms · 1 bathrooms" | Proper singular/plural forms in English and Kiswahili (web i18next plurals, Flutter ICU plurals) |
| Booking confirmation | A one-line alert | A confirmation panel with reference, service, date and time, total, plus *Track booking* and *My bookings* |
| Landing hero | A decorative mock card, later an empty right half | A restrained "Every booking includes" panel using the real lowest catalogue price |
| Provider dashboard | Company greeted as "Hello, Usafi"; analytics above the actual work; two large money cards | Companies greeted by business name; job requests and active jobs come first; one compact earnings summary |
| Provider wording | Customer-facing labels on provider screens | Provider-specific status labels ("Job assigned", "On the way"); "provider" instead of "cleaner" where companies are included |
| Review step | Doubled icon in the materials notice | Single icon |
| Admin | Blank tables when filters matched nothing; reassignment folded into "needs a provider" | Helpful empty states with *Clear filters*; reassignments listed separately under "Needs attention" |
| Flutter | No way to report a problem; plain confirmation | *Report an issue* dialog (categories, validation); detailed confirmation card |
| Performance | One 588 KB bundle for every visitor | Customer, provider and admin areas are lazy-loaded; the public entry bundle is now 478 KB |

**Verification after the polish**

Backend 53 ✓ · Web lint, type-check, 18 tests and build ✓ · Flutter analyze and 7 tests ✓ · full UI journey (book → assign → accept → progress → confirm → cash → close → review → admin) ✓ with no browser errors · no horizontal overflow at 320 or 390 px · Docker web image rebuilt.

**Remaining limitations**

- The public entry bundle (478 KB, 145 KB gzipped) is mostly framework and library code. Splitting it further would need vendor chunking.
- There's no photography yet. The brand relies on typography, icons and real data until a professional shoot is available; stock imagery was deliberately avoided.
- Flutter web needs internet access for the CanvasKit renderer (or a build with `--no-web-resources-cdn`). Android and iOS builds are unaffected.

## Backend hardening: performance, concurrency, resilience (2026-10-02)

I audited the backend against a realistic dataset (150k bookings, 30k customers, 300 providers), then fixed what the evidence showed. The full write-up:

- [ARCHITECTURE_ASSESSMENT.md](ARCHITECTURE_ASSESSMENT.md): findings by severity.
- [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md): measured before and after.
- [PRODUCTION_ARCHITECTURE.md](PRODUCTION_ARCHITECTURE.md): pilot and growth topology.
- [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md).
- Decision records in [architecture/](architecture/).

**Concurrency and correctness**

- 9 new race and idempotency tests failed 9/9 on the old code and now pass 9/9. The fixes:
  - booking and provider row locks with a fixed lock order;
  - optimistic `version_id` columns;
  - a database-enforced "one open assignment per booking";
  - idempotent booking creation (`Idempotency-Key`, now honoured; Flutter already sent it and the web app now does too);
  - idempotent accept and cash confirmation;
  - settlement payout locking;
  - an idempotent payment-gateway callback ledger.
- Fixed a functional bug: a cleaner holding two overlapping offers could accept neither.

**Performance**

- At 60 concurrent users, one 2-vCPU container went from p50 1,100 ms / p99 10 s to p50 48 ms / p99 860 ms.
- Cleaner endpoints dropped from 13–85 s to under 0.4 s at p50.
- Per-request SQL fell sharply, e.g. completed jobs from 2,883 statements to 9, and availability from 54 to 6.
- Query-driven indexes, e.g. the expiry scan from 47 ms to 0.04 ms.

**Resilience and operations**

- A dedicated `worker` service (offer expiry plus a notification outbox with retries and backoff).
- `/health/live` and `/health/ready`, and Prometheus `/metrics`.
- Request IDs on every log line, slow-request logging, and per-request query counts.
- Database statement, lock and pool timeouts, with 503/409 responses instead of hangs.
- Graceful shutdown.
- Trusted-proxy handling: the client IP can no longer be spoofed, and the audit log now records IPs.
- A multi-stage non-root image, and edge rate limiting on credential endpoints.

**Decisions**

- PostgreSQL row locking and the worker: **adopted**.
- Redis, HAProxy and Kafka: **deferred**, each with explicit triggers.
- In-process domain events after commit: **adopted** as the future integration seam.

**Verification**

Backend 80 tests ✓ (53 → 80) · web type-check and 18 tests ✓ · Flutter 46 tests ✓ · full UI journey on the Docker stack ✓ with no browser errors · live drills: database outage, graceful restarts and proxy-header spoofing ✓.

## Flutter customer app: premium UI/UX audit, finalized (2026-10-02)

I finished the in-progress mobile redesign and verified it **on a physical Android phone** (Z2359, Android 13). I ran the complete customer journey there through the real API in English and in Kiswahili, with screenshots in [screenshots/mobile/](screenshots/mobile/).

**What the redesign delivers**

- **Design system** (`lib/ui/theme.dart`): a bundled DM Sans typeface (no font CDN), the light SafishaCon palette, a spacing scale and one button hierarchy. The navigation, chip and input themes are restrained, with no dark theme.
- **Navigation:** three tabs (Home, Bookings, Profile), and the primary action is always *Book a cleaning*.
- **Home** is built around intent: "What would you like cleaned?", your next cleaning with *Track booking*, services with starting prices and a detail sheet, how it works, and "equipment included".
- **Booking flow:** 5 steps with a compact `2/5` progress bar:
  1. service;
  2. property (type chips and steppers);
  3. location (supported areas, optional notes);
  4. schedule (day strip plus live slots, unavailable ones greyed out);
  5. review and pay, with edit links, the server-calculated price, cash "pay after cleaning" (digital methods stay hidden until a real gateway exists).

  A sticky total sits above the button. The final button says *Confirm booking* and can't double-submit: an `Idempotency-Key` keeps retries safe.
- **Success screen** with reference, schedule, area and total, plus *Track booking* and *Back to home*.
- **Booking tracking:**
  - human status headlines for every stage ("Finding your cleaning professional", "Your cleaner is on the way"…);
  - the cleaner (initials, verified, rating);
  - a step timeline;
  - completion with *Confirm completion* and *Report an issue*;
  - review;
  - cash status;
  - support and cancel.
- **Profile:** details, EN/SW switch (persisted, without losing state), support, and sign out with confirmation.
- **Errors, empty and loading states:** friendly messages for network failures, timeouts and expired sessions, with retry; booking input is preserved on failure.

**Fixed during finalization**

- **Refreshes could be silently dropped.** A refresh requested while another was in flight (15 s poll, app resume, pull-to-refresh) was ignored. After submitting a review the screen could keep showing the stale form; on the phone this caused a failed run. A new `RefreshGate` queues one follow-up refresh instead, on the booking, Home and Bookings screens, with a unit test.
- **Sticky total alignment:** it floated mid-row and, when first fixed, overflowed at 320 px with 2.0× font. It is now right-aligned and wraps safely, verified by the layout tests.
- **Screen order and visibility:** the assigned cleaner now comes before the timeline, and the timeline starts open while a booking is live.
- **Copy:** the completion question was shown twice; the success screen no longer refers to "progress below" that doesn't exist, and has no redundant title.
- **Phone numbers** are formatted as `+255 713 000 002`.
- **The journey test** used Flutter's English-only `pageBack()`, so the Kiswahili run always failed at its last step. Fixed.

**Verification:** `flutter analyze` clean · 48 tests ✓ · device journey EN ✓ (SC-TKM3GW) and SW ✓ (SC-UVNRU3) · release APK build to be done separately.

**Remaining limitations:**

- Digital payments are hidden until a gateway is integrated.
- There is no live GPS or chat; the UI claims neither.
- There is no in-app call action yet (the number can be copied).
- iOS hasn't been run on a device.
