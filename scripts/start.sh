#!/usr/bin/env bash
set -euo pipefail

echo "[startup] running migrations and starting server..."
echo "[startup] DATABASE_URL=${DATABASE_URL:-<not set>}"

# Run alembic migrations if available
if command -v alembic >/dev/null 2>&1; then
  echo "[startup] running alembic upgrade head"
  alembic upgrade head || echo "[startup] alembic returned non-zero"
else
  echo "[startup] alembic not found, skipping migrations"
fi

# Start Gunicorn with Uvicorn worker
exec gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:${PORT} --workers 1 --log-level info
