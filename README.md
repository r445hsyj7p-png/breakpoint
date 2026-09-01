# Breakpoint — From Attack Technique to Action

Übersetzt Red-Team-/Pentest-Findings (MITRE-ATT&CK-Techniken) in priorisierte,
geschäftlich verständliche Maßnahmen. Vollständiger Projektkontext, Architektur
und Roadmap: [`docs/projektauftrag.md`](docs/projektauftrag.md).

Dies ist **Schritt 1**: ein lauffähiges Grundgerüst ohne Cloud-Abhängigkeiten,
noch ohne Analyzer-Logik oder LLM-Anbindung.

## Voraussetzungen

- Docker + Docker Compose (v2, `docker compose ...`)
- Keine Internetverbindung zur Laufzeit nötig — nur beim ersten Build, um
  Basis-Images und Abhängigkeiten herunterzuladen.

## Lokal starten

```bash
cp .env.example .env
# .env bei Bedarf anpassen (Passwörter etc.)

docker compose -f infra/docker-compose.yml up --build
```

Das startet drei Services:

| Service    | URL                         | Beschreibung                                   |
|------------|------------------------------|-------------------------------------------------|
| `db`       | `127.0.0.1:5432`             | PostgreSQL 16                                    |
| `backend`  | http://127.0.0.1:8000        | FastAPI. Wendet beim Start automatisch alle Alembic-Migrationen an und seedet den Grunddatensatz (15 Taktiken, ~190 Techniken, Capabilities, Controls, Mappings). |
| `frontend` | http://127.0.0.1:5173        | Vite-Dev-Server mit Hot-Reload                   |

Alle drei Services binden ausschließlich an `127.0.0.1` (nicht an alle
Netzwerk-Interfaces) — auch in der lokalen Entwicklung, siehe
[`docs/projektauftrag.md`](docs/projektauftrag.md) Abschnitt 8.

`GET http://127.0.0.1:8000/health` liefert `{"status": "ok"}`.

Zum Beenden: `docker compose -f infra/docker-compose.yml down` (Datenbank-Volume
bleibt erhalten; mit `down -v` auch das Volume entfernen).

## Backend ohne Docker (lokale Entwicklung)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# gegen eine lokal laufende Postgres-Instanz, z.B.:
export DATABASE_URL="postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint"

alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Tests:

```bash
export DATABASE_URL="postgresql+psycopg://breakpoint:breakpoint@localhost:5432/breakpoint_test"
pytest
```

Die Tests laufen gegen eine eigene Datenbank (`breakpoint_test`), legen ihr
Schema per `Base.metadata.create_all` an und räumen danach wieder auf.

## Frontend ohne Docker (lokale Entwicklung)

```bash
cd frontend
npm install
npm run dev
```

## VPS/Produktions-Deploy

Separates Compose-File mit produktivem Frontend-Build (nginx statt Vite-Dev-
Server) und ohne öffentlich erreichbare `db`/`backend`-Ports — Details und
Hintergrund in [`docs/projektauftrag.md`](docs/projektauftrag.md) Abschnitt 10h.

> ⚠️ **Nur als Proof-of-Concept ohne echte Kundendaten freigegeben.** Die App
> hat noch keinen Auth-Layer (kommt erst in Schritt 7, siehe Abschnitt 12
> Frage 3). `docker-compose.prod.yml` macht das Frontend auf Port 80 ohne
> jeden Zugriffsschutz öffentlich erreichbar. Für echte Findings/Engagements
> vorher zwingend einen Zugriffsschutz vorschalten (VPN, IP-Allowlist, Basic
> Auth) oder den OIDC-Layer umsetzen.

```bash
cp .env.example .env
# .env anpassen: mindestens POSTGRES_PASSWORD setzen, ggf. PUBLIC_HTTP_PORT

docker compose -f infra/docker-compose.prod.yml up --build -d
```

Danach ist die App unter `http://<VPS-IP-oder-Domain>:${PUBLIC_HTTP_PORT:-80}`
erreichbar — nginx liefert das gebaute Frontend aus und proxied `/api/` intern
zum Backend-Container. `db` und `backend` sind ausschließlich über das
interne Docker-Netzwerk erreichbar, kein Host-Port-Publish.

Für TLS (empfohlen, sobald die Instanz über eine feste Domain erreichbar ist):
einen weiteren Reverse Proxy (z. B. Caddy oder nginx + certbot) vor den
`frontend`-Service schalten, oder `frontend/nginx.conf` um eine `listen 443
ssl`-Server-Direktive mit Zertifikat erweitern — ist in diesem POC-Setup
bewusst nicht enthalten.

## Projektstruktur

```
breakpoint/
├── backend/            FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/        Endpunkte (aktuell: /health)
│   │   ├── models/      SQLAlchemy-Modelle
│   │   ├── schemas/     Pydantic-Schemas (ab Schritt 2)
│   │   └── core/        Settings, DB-Session
│   ├── alembic/         Migrationen
│   ├── scripts/         Seed-Daten & Seed-Skript
│   └── tests/
├── frontend/            React + TypeScript + Vite + Tailwind CSS v4
│   └── src/
│       ├── components/  Layout (Sidebar, Topbar)
│       └── pages/        Dashboard, Engagements, Analyzer, Techniken, Portfolio, Knowledge Base, Reports
├── infra/
│   └── docker-compose.yml
├── docs/
│   └── projektauftrag.md   Vollständiger Projektauftrag inkl. Datenmodell, Architektur, Roadmap
├── .env.example
└── README.md
```

## Stand Schritt 1 (Definition of Done)

- [x] `docker compose -f infra/docker-compose.yml config` validiert fehlerfrei (Compose-Datei syntaktisch/semantisch korrekt); ein vollständiger `docker compose up --build`-Lauf konnte in der Entwicklungsumgebung dieses Auftrags nicht verifiziert werden, da das Docker-Image-Registry (`production.cloudfront.docker.com`) dort per Netzwerk-Policy geblockt ist. Alle Einzelkomponenten wurden stattdessen nativ (venv/npm) gegen eine lokale Postgres 16 validiert — siehe Punkte unten. **Vor dem ersten produktiven Einsatz bitte einmal `docker compose -f infra/docker-compose.yml up --build` in einer Umgebung mit Docker-Hub-Zugriff gegentesten.**
- [x] `GET /health` liefert `200 OK` (verifiziert: `uvicorn` lokal gestartet, `curl` liefert `{"status":"ok"}`)
- [x] Alembic-Migration läuft durch, `tactic`- und `technique`-Tabellen sind vollständig befüllt (14 Taktiken, 188 Techniken, 10 spezifische + 14 Taktik-Standard-Mappings — verifiziert gegen lokale Postgres 16 via `psql`)
- [x] Frontend zeigt das Grundlayout mit funktionierender Tab-Navigation (noch ohne Live-Daten); `npm run build` läuft fehlerfrei durch (Typecheck + Vite-Build)
- [x] README beschreibt lokalen Setup-Prozess vollständig, ohne Cloud-Voraussetzungen
- [x] Kein Code-Pfad ruft eine externe URL zur Laufzeit auf (keine CDN-Fonts — Fonts sind über `@fontsource` lokal gebündelt und im Produktions-Build als lokale Assets verifiziert, keine externen APIs)
- [x] Alle Compose-Services binden ausschließlich an `127.0.0.1` (siehe `infra/docker-compose.yml`)

Details zu den Korrekturen gegenüber dem HTML-Prototyp (Sub-Technique-Fallback,
Control als eigene Entität, Auflösung von Mehrfach-Taktik-Zuordnungen) stehen
als Kommentare im jeweiligen Code sowie in
[`docs/projektauftrag.md`](docs/projektauftrag.md) Abschnitt 5.

Nächste Schritte (nicht Teil von Schritt 1): siehe
[`docs/projektauftrag.md`](docs/projektauftrag.md) Abschnitt 11.
