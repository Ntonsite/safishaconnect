"""Prometheus metrics.

Low-cardinality by design: HTTP metrics are labelled by *route template*
(``/api/v1/bookings/{booking_id}``), never by raw path, user or booking id.
Business metrics come from domain events, so they count committed work only.

Multiple uvicorn workers: set ``PROMETHEUS_MULTIPROC_DIR`` (the container entrypoint
does) and every worker's samples are aggregated at scrape time.
"""

import os
import time

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import func, select

from app.core import events
from app.core.logging import get_logger

log = get_logger("metrics")
MULTIPROC = bool(os.environ.get("PROMETHEUS_MULTIPROC_DIR"))

HTTP_REQUESTS = Counter("safisha_http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "safisha_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_IN_PROGRESS = Gauge("safisha_http_requests_in_progress", "In-flight requests", multiprocess_mode="livesum")
DB_QUERIES = Histogram(
    "safisha_db_queries_per_request", "SQL statements per request", buckets=(1, 2, 5, 10, 20, 50, 100, 250)
)
DB_POOL_CHECKED_OUT = Gauge(
    "safisha_db_pool_checked_out", "Connections in use by this process", multiprocess_mode="livesum"
)
DB_POOL_CAPACITY = Gauge("safisha_db_pool_capacity", "pool_size + max_overflow per process", multiprocess_mode="max")

BOOKINGS_CREATED = Counter("safisha_bookings_created_total", "Bookings created")
BOOKINGS_CANCELLED = Counter("safisha_bookings_cancelled_total", "Bookings cancelled")
ASSIGNMENT_EVENTS = Counter("safisha_assignment_events_total", "Assignment lifecycle events", ["outcome"])
ASSIGNMENT_ACCEPT_LATENCY = Histogram(
    "safisha_assignment_accept_latency_seconds",
    "Offer sent -> provider accepted",
    buckets=(30, 60, 120, 300, 600, 900, 1800, 3600),
)
PAYMENTS_CONFIRMED = Counter("safisha_payments_confirmed_total", "Payments confirmed", ["method"])
PAYMENT_FAILURES = Counter("safisha_payment_confirmation_failures_total", "Rejected payment confirmations", ["code"])
JOB_RUNS = Counter("safisha_background_job_runs_total", "Background job runs", ["job", "result"])
JOB_LAST_SUCCESS = Gauge(
    "safisha_background_job_last_success_timestamp_seconds", "Last successful run", ["job"], multiprocess_mode="max"
)


def observe_request(method: str, route: str, status: int, seconds: float, queries: int) -> None:
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_LATENCY.labels(method, route).observe(seconds)
    DB_QUERIES.observe(queries)


def observe_pool(engine) -> None:
    pool = engine.pool
    DB_POOL_CHECKED_OUT.set(pool.checkedout())
    DB_POOL_CAPACITY.set(pool.size() + pool._max_overflow)  # noqa: SLF001 - no public accessor


def job_succeeded(job: str) -> None:
    JOB_RUNS.labels(job, "ok").inc()
    JOB_LAST_SUCCESS.labels(job).set(time.time())


def job_failed(job: str) -> None:
    JOB_RUNS.labels(job, "error").inc()


# --- business metrics from committed domain events ------------------------------------------
_ASSIGNMENT_OUTCOMES = {
    events.ASSIGNMENT_OFFERED: "offered",
    events.ASSIGNMENT_ACCEPTED: "accepted",
    events.ASSIGNMENT_REJECTED: "rejected",
    events.ASSIGNMENT_EXPIRED: "expired",
    events.ASSIGNMENT_UNMATCHED: "unmatched",
}


def _on_event(evt: events.DomainEvent) -> None:
    if evt.name == events.BOOKING_CREATED:
        BOOKINGS_CREATED.inc()
    elif evt.name == events.BOOKING_CANCELLED:
        BOOKINGS_CANCELLED.inc()
    elif evt.name in _ASSIGNMENT_OUTCOMES:
        ASSIGNMENT_EVENTS.labels(_ASSIGNMENT_OUTCOMES[evt.name]).inc()
        if evt.name == events.ASSIGNMENT_ACCEPTED and evt.data.get("wait_seconds") is not None:
            ASSIGNMENT_ACCEPT_LATENCY.observe(evt.data["wait_seconds"])
    elif evt.name == events.PAYMENT_CONFIRMED:
        PAYMENTS_CONFIRMED.labels(evt.data.get("method", "UNKNOWN")).inc()


events.subscribe("*", _on_event)


class OperationalStateCollector:
    """Live marketplace gauges read from PostgreSQL at scrape time (one indexed GROUP BY)."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def collect(self):
        from app.models import Booking
        from app.models.enums import TERMINAL_STATUSES

        family = GaugeMetricFamily("safisha_open_bookings", "Bookings not yet closed/cancelled", labels=["status"])
        try:
            with self._session_factory() as db:
                rows = db.execute(
                    select(Booking.status, func.count())
                    .where(Booking.status.not_in(TERMINAL_STATUSES))
                    .group_by(Booking.status)
                ).all()
            for status, count in rows:
                family.add_metric([status.value], count)
        except Exception:  # metrics must never fail because the database is briefly unavailable
            log.warning("metrics.open_bookings_unavailable")
        yield family


def render(session_factory) -> tuple[bytes, str]:
    if MULTIPROC:
        from prometheus_client import multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        from prometheus_client import REGISTRY as registry
    extra = CollectorRegistry()
    extra.register(OperationalStateCollector(session_factory))
    return generate_latest(registry) + generate_latest(extra), CONTENT_TYPE_LATEST
