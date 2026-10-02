# ADR-005: A small PostgreSQL-backed worker for background jobs (no broker)

- **Status:** Adopted.
- **Date:** 2 October 2026

## Context

SafishaCon has work that must happen without a user request:

1. **Offer expiry.** A provider who does not answer within the TTL (30 min by default, set by an admin) loses the offer, and the booking goes to the next eligible provider, or to admins if there is none. This must not depend on a browser staying open, a refresh, or a timer inside one API process.
2. **External notifications** (SMS or push, once a provider is configured) must not run inside the booking transaction. They need timeouts and retries.

### What I found

- An asyncio loop inside **every** API process ran expiry.
  - Restarts paused it.
  - More replicas multiplied it.
  - It shared one transaction across a whole batch.
  - It locked assignment rows in the opposite order to user requests, which caused a **deadlock** in testing.
- SMS was called synchronously before commit.

## Decision

- **A dedicated worker process,** `python -m app.worker`: the `worker` service in docker compose, built from the same image.
  - It runs every job every `WORKER_INTERVAL_SECONDS` (30 s).
  - It touches a heartbeat file each pass; the container health check requires the heartbeat to be younger than 2 minutes.
  - It optionally exposes Prometheus metrics on `WORKER_METRICS_PORT`.
  - On SIGTERM it finishes the current unit of work and exits.
- **No broker.** Job state lives in PostgreSQL:
  - Offer expiry scans `provider_assignments WHERE status='OFFERED' AND expires_at <= now()` using a partial index (0.04 ms).
  - Each offer is processed in **its own transaction**: lock the booking with `SKIP LOCKED`, re-read, expire, re-dispatch, commit. A booking that a user is acting on at that moment is skipped and retried next pass. One failure never blocks the others.
  - The notification outbox claims one message at a time (`SKIP LOCKED`) and commits each send. Backoff is 1, 2, 4, 8… minutes (capped at 60). It marks a message `FAILED` after `NOTIFICATION_MAX_ATTEMPTS`. Senders must use `EXTERNAL_CONNECT_TIMEOUT_SECONDS` and `EXTERNAL_READ_TIMEOUT_SECONDS`.
- **Safe with any number of workers,** for example two running during a rolling deploy.
- **Local development** can still run jobs inside the API (`BACKGROUND_JOBS_ENABLED=true`, the default). Compose sets it to `false` for the API.

## Alternatives considered

| Option | Why not now |
|---|---|
| FastAPI `BackgroundTasks` | Runs after the response, in the same process, and is lost on restart. That's fine for fire-and-forget, but not for an expiry deadline. |
| Celery/RQ + Redis or RabbitMQ | Adds a broker to operate and monitor, plus a second source of truth for job state. Our jobs are periodic scans of PostgreSQL state, so a broker would only re-deliver what a query already finds. |
| pg_cron / a scheduled SQL function | Moves dispatch logic (eligibility, ranking, notifications) into SQL, splitting the domain logic. |
| Cloud scheduler hitting an HTTP endpoint | Workable, but needs an authenticated internal endpoint, and the per-item transactions still need code. |

## Failure behaviour

| Failure | Effect |
|---|---|
| Worker down | Offers stay OFFERED past their deadline. Providers can no longer accept them, because acceptance re-checks `expires_at`. Bookings wait in "finding a cleaner" until the worker returns, then re-dispatch on the first pass. The health check turns unhealthy; alert on `safisha_background_job_last_success_timestamp_seconds`. |
| Worker killed mid-pass | The open transaction rolls back, so nothing is half-done. The next pass picks the work up again. |
| PostgreSQL down | Each pass fails and is logged (`jobs.failed`). The loop continues and recovers on its own. |
| SMS gateway down | Messages back off and retry, then are marked `FAILED`. Bookings are unaffected (tested). |

## Revisit when

- Jobs need sub-second scheduling, very high fan-out, or long-running work such as report generation or image processing. Then add a real queue (RQ or Celery on Redis, or SQS) for *those* jobs.
- More than one kind of worker needs independent scaling.
