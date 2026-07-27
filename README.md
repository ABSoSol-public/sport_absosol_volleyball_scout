# ABSoSol Volleyball Scout

Eigene Scouting- und Analyse-Software für Volleyball: **Live-Scouting** mit vollständiger
Regelabbildung (Punkte, Side-Out, Rotation, Sätze, Wechsel, Auszeiten, Undo) und
**Import bestehender DataVolley-Dateien** (`.dvw`, Upload auf der Matches-Seite).
Login-pflichtig mit Rollen (admin/viewer). Statistik-Auswertung folgt (Roadmap 2.2).

## Architektur

| Komponente | Technologie | Ort |
|---|---|---|
| API + Live-Engine | Python, FastAPI, SQLAlchemy 2, Alembic | `backend/` |
| Datenbank | MariaDB 11 | Docker-Volume |
| Frontend | Vue 3 + Vite (SPA), ausgeliefert per nginx | `frontend/` |

Das Live-Scouting arbeitet mit **Event-Sourcing**: jede Eingabe (Satzstart, Rally,
Wechsel, Auszeit) wird als Event in `live_events` gespeichert; der Spielstand entsteht
deterministisch durch Replay in der `MatchEngine` (`backend/app/engine/`). Undo löscht
das letzte Event — wie das „Undo End Rally" im DataVolley-Vorbild.

Scout-Codes folgen dem DataVolley-Main-Code (`5SQ=`, `a7AT#`, `14AH+45`, …); der Parser
liegt in `backend/app/engine/scout_code.py`.

## Lokal starten (Docker)

Es gibt **keinen lokalen DB-Container** — einzige Datenbank ist die MariaDB auf
der Synology, auch für die lokale Entwicklung. Deshalb braucht die `.env` die
`SYNOLOGY_DB_*`-Zugangsdaten (Vorlage: `.env.example`).

```bash
cp .env.example .env   # SYNOLOGY_DB_* ausfüllen
docker compose up --build
```

- Frontend: http://localhost:8080
- API-Doku (OpenAPI): http://localhost:8000/docs

Die Alembic-Migrationen laufen beim Backend-Start automatisch (`docker-entrypoint.sh`).

## Entwicklung ohne Docker

```bash
# Backend (braucht eine erreichbare MariaDB, siehe VOLLEYSCOUT_DATABASE_URL)
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload

# Tests (laufen ohne Datenbank, SQLite in-memory)
.venv/bin/python -m pytest

# Frontend (Dev-Server mit API-Proxy auf localhost:8000)
cd frontend
npm install
npm run dev
```

## Login

Die App ist komplett login-pflichtig (keine Registrierung). Benutzer anlegen /
Passwort zurücksetzen: `./create-user.sh <name> <passwort> [admin|viewer]` —
`viewer` bekommt Nur-Lese-Zugriff. Session-Signierung über
`VOLLEYSCOUT_SECRET_KEY` in der `.env` (siehe `.env.example`).

## Typischer Ablauf

0. Anmelden (Benutzer siehe oben).
1. Unter **Teams** beide Teams samt Kader anlegen.
2. Unter **Matches** ein Match anlegen und **Live-Scouting** öffnen.
3. Aufstellungen (Zonen 1–6) und Aufschlagteam setzen → Satz starten.
4. Pro Ballwechsel optional Scout-Codes erfassen, dann „+ Punkt"-Button des
   Gewinnerteams — Rotation, Aufschlagrecht, Satz- und Matchende übernimmt die Engine.

## Deployment auf der Synology

Gleiches Muster wie beim `yugioh_database`-Projekt: **Quellcode per `git clone`
auf die NAS, dort mit `docker-compose --env-file .env up -d --build` bauen und
starten** — dieselbe `docker-compose.yml` wie lokal, keine Registry. Erreichbar
ist die App über den DSM-Reverse-Proxy unter `volleyball.<ddns-domain>.myds.me`
(Subdomain-Muster, feste Container-IP `172.29.0.10` als Proxy-Ziel).
**Komplette Anleitung: `docs/DEPLOYMENT-SYNOLOGY.md`.**

## Roadmap & Doku

- Synology-Deployment (Schritt für Schritt): `docs/DEPLOYMENT-SYNOLOGY.md`
- Architektur (Komponenten, Event-Sourcing, Engine, Konfiguration): `docs/ARCHITEKTUR.md`
- API-Referenz (Endpunkte, Beispiele, Fehlersemantik): `docs/API.md` —
  interaktiv unter http://localhost:8000/docs
- Datenbank (Schema, Event-Payloads, Migrationen, Betrieb): `docs/DATENBANK.md`
- Versionsplan: `docs/ROADMAP.md`
- DVW-Dateiformat: `docs/DVW-FORMAT.md`
- Vollständige DataVolley-4-Referenz (Scout-Code, Formeln): Tiefenrecherche im
  übergeordneten Projektordner (`../recherche/`, nicht Teil dieses Repos)
