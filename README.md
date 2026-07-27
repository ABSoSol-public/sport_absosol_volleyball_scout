# ABSoSol Volleyball Scout

Eigene Scouting- und Analyse-Software für Volleyball: Live-Scouting mit vollständiger
Regelabbildung (Punkte, Side-Out, Rotation, Sätze, Wechsel, Auszeiten, Undo) plus — in
späteren Versionen — Import und Auswertung bestehender DataVolley-Dateien (`.dvw`).

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

```bash
cp .env.example .env   # Werte bei Bedarf anpassen
docker compose up --build
```

- Frontend: http://localhost:8080
- API-Doku (OpenAPI): http://localhost:8000/docs
- MariaDB: localhost:3306 (nur auf 127.0.0.1 gebunden)

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

## Typischer Ablauf

1. Unter **Teams** beide Teams samt Kader anlegen.
2. Unter **Matches** ein Match anlegen und **Live-Scouting** öffnen.
3. Aufstellungen (Zonen 1–6) und Aufschlagteam setzen → Satz starten.
4. Pro Ballwechsel optional Scout-Codes erfassen, dann „+ Punkt"-Button des
   Gewinnerteams — Rotation, Aufschlagrecht, Satz- und Matchende übernimmt die Engine.

## Roadmap & Doku

- Versionsplan: `docs/ROADMAP.md`
- DVW-Dateiformat: `docs/DVW-FORMAT.md`
- Vollständige DataVolley-4-Referenz (Scout-Code, Formeln): Tiefenrecherche im
  übergeordneten Projektordner (`../recherche/`, nicht Teil dieses Repos)
