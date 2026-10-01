#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "Seeding database (idempotent)..."
  python -m app.seed
fi

exec "$@"
