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
# --reload beobachtet Quelldateien und ist nur für die lokale Entwicklung
# (bind-gemountete Quellen, infra/docker-compose.yml) sinnvoll; in Produktion
# (infra/docker-compose.prod.yml) unnötiger Overhead ohne Nutzen, da dort
# nichts gemountet wird und sich die Quellen im Image nie ändern.
if [ "${UVICORN_RELOAD:-true}" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
