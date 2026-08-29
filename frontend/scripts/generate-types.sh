#!/bin/sh
# Generiert frontend/src/lib/api-types.ts aus dem OpenAPI-Schema des Backends
# — ohne dass das Backend dafür laufen muss (docs/projektauftrag.md
# Abschnitt 10b.2). Kein manuell gepflegtes Interface, das aus dem Tritt
# geraten könnte.
set -e
cd "$(dirname "$0")/.."

BACKEND_DIR="../backend"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"

if [ ! -x "$BACKEND_PYTHON" ]; then
  echo "Backend-venv nicht gefunden unter $BACKEND_DIR/.venv — siehe README (Backend ohne Docker)." >&2
  exit 1
fi

TMP_SCHEMA="$(mktemp)"
trap 'rm -f "$TMP_SCHEMA"' EXIT

(cd "$BACKEND_DIR" && ./.venv/bin/python -c "import json; from app.main import app; print(json.dumps(app.openapi()))") > "$TMP_SCHEMA"

npx openapi-typescript "$TMP_SCHEMA" -o src/lib/api-types.ts

echo "src/lib/api-types.ts aktualisiert."
