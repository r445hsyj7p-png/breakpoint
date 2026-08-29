#!/bin/sh
set -e

echo "Warte auf Postgres..."
until python -c "
import sys
from sqlalchemy import create_engine
from app.core.config import settings
try:
    create_engine(settings.database_url).connect().close()
except Exception:
    sys.exit(1)
"; do
  sleep 1
done

echo "Wende Alembic-Migrationen an..."
alembic upgrade head

echo "Seede Grunddaten (idempotent)..."
python -m scripts.seed

echo "Starte Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
