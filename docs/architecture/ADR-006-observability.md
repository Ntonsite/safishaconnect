# ADR-006: Structured logs, request correlation and Prometheus metrics; Grafana-ready, not Grafana-bundled

- **Status:** Adopted.
- **Date:** 2 October 2026

## Context

The MVP had JSON access logs and an `X-Request-ID`, but:

- no metrics;
- no liveness/readiness split;
- logs written inside services were not linked to the request;
- no per-request database cost;
- no visibility into slow requests.

Running a Prometheus + Grafana + Loki stack from day one would be a lot of operational weight for a pilot.

## Decision

**Logs (stdout, JSON):**

- Every line written while serving a request carries `request_id`, and `user_id` once authenticated. This comes from a request context set by a pure ASGI middleware.
- The access log records the method, route template, status, duration and **SQL statement count**.
- Requests slower than `SLOW_REQUEST_MS` (1 s) log at WARNING as `http.slow_request`.
- Secrets are redacted by key: passwords, tokens, authorization, API keys.

**Correlation:**

- nginx forwards the caller's `X-Request-ID` or generates one.
- Unsafe IDs are replaced, which prevents log and header injection.
- The ID is returned on every response and included in every error body.

**Metrics:** `GET /metrics` in Prometheus format.

| Area | Metrics |
|---|---|
| HTTP | `safisha_http_requests_total{method,route,status}`, `safisha_http_request_duration_seconds{method,route}` (labelled by **route template**, never by ID), `safisha_http_requests_in_progress`, `safisha_db_queries_per_request` |
| DB pool | `safisha_db_pool_checked_out`, `safisha_db_pool_capacity` |
| Business (from committed domain events) | `safisha_bookings_created_total`, `safisha_bookings_cancelled_total`, `safisha_assignment_events_total{outcome}`, `safisha_assignment_accept_latency_seconds`, `safisha_payments_confirmed_total{method}`, `safisha_payment_confirmation_failures_total{code}` |
| Jobs | `safisha_background_job_runs_total{job,result}`, `safisha_background_job_last_success_timestamp_seconds{job}` |
| Live state | `safisha_open_bookings{status}`, one indexed `GROUP BY` at scrape time |

- Multiple uvicorn processes are aggregated through `PROMETHEUS_MULTIPROC_DIR`, which the entrypoint sets.
- `/metrics` is not proxied by nginx, and `METRICS_TOKEN` can require a bearer token.
- No customer data, amounts per person, or identifiers appear in metric labels.

**Health:**

- `/health/live`: the process is up. It never touches dependencies, so a database blip cannot cause restart storms.
- `/health/ready`: the database answers within 2 s. Otherwise it returns 503 `{"status":"unavailable"}` with no infrastructure details.

**Database:** compose enables `pg_stat_statements` for slow-query investigation.

## Not adopted yet

- **A bundled Prometheus/Grafana stack.** Point a hosted Prometheus or Grafana Cloud (or the platform's agent) at `/metrics` when deploying.
- **Distributed tracing (OpenTelemetry).** Revisit when there is more than one service.

## Suggested first alerts

| Alert | Condition |
|---|---|
| API errors | 5xx rate above 1% for 5 min |
| Latency | p95 `safisha_http_request_duration_seconds` above 1 s for 10 min |
| Worker | `time() - safisha_background_job_last_success_timestamp_seconds{job="offer_expiry"}` above 300 |
| Matching | `safisha_assignment_events_total{outcome="unmatched"}` rising: bookings with no eligible cleaner |
| Pool | `safisha_db_pool_checked_out / safisha_db_pool_capacity` above 0.8 for 5 min |
| Money | any `safisha_payment_confirmation_failures_total{code="AMOUNT_MISMATCH"}` |
