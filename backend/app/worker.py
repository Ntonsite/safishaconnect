"""Dedicated background worker: ``python -m app.worker``.

Runs the PostgreSQL-backed jobs (offer expiry + re-dispatch, notification outbox)
on a fixed interval, independent of API traffic, browsers or API restarts.

* No broker: jobs claim rows with ``FOR UPDATE SKIP LOCKED``, so running two workers
  (e.g. during a rolling deploy) is safe.
* Graceful: SIGTERM/SIGINT finishes the current unit of work, then exits.
* Observable: touches a heartbeat file each pass (container health check) and can
  expose Prometheus metrics on WORKER_METRICS_PORT.

See docs/architecture/ADR-005-background-jobs.md.
"""

import os
import signal
import threading
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.services.jobs import run_all_once

HEARTBEAT = Path(os.environ.get("WORKER_HEARTBEAT_FILE", "/tmp/safisha-worker.heartbeat"))  # noqa: S108

log = get_logger("worker")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    stop = threading.Event()

    def _shutdown(signum, _frame) -> None:
        log.info("worker.stopping", extra={"signal": signal.Signals(signum).name})
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    port = os.environ.get("WORKER_METRICS_PORT")
    if port and settings.metrics_enabled:
        from prometheus_client import start_http_server

        start_http_server(int(port))

    log.info("worker.started", extra={"interval_s": settings.worker_interval_seconds})
    while not stop.is_set():
        started = time.monotonic()
        run_all_once()
        HEARTBEAT.write_text(str(int(time.time())))
        stop.wait(max(0.0, settings.worker_interval_seconds - (time.monotonic() - started)))
    engine.dispose()
    log.info("worker.stopped")


if __name__ == "__main__":
    main()
