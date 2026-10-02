#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  # Safe when several replicas start together: migrations take a PostgreSQL advisory lock.
  alembic upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "Seeding database (idempotent)..."
  python -m app.seed
fi

if [ "$1" = "serve" ]; then
  # Production server. No --reload. One process per WEB_CONCURRENCY; see
  # docs/PRODUCTION_ARCHITECTURE.md ("Process model") before changing it.
  if [ "${WEB_CONCURRENCY:-1}" -gt 1 ]; then
    # Aggregate Prometheus metrics across worker processes.
    export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}"
    rm -rf "$PROMETHEUS_MULTIPROC_DIR" && mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
  fi
  exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${WEB_CONCURRENCY:-1}" \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
    --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-20}" \
    --timeout-keep-alive "${KEEP_ALIVE_SECONDS:-15}" \
    --no-server-header --no-access-log
fi

exec "$@"
