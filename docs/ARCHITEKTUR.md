# Architektur

Stand: Version 1.0 (2026-07-27)

## Überblick

```
┌────────────────┐      /api (Proxy)      ┌────────────────┐        ┌──────────────────┐
│   Frontend     │ ─────────────────────► │    Backend     │ ─────► │ MariaDB 10.11    │
│ Vue 3 + Vite   │                        │ FastAPI + SQLA │        │ auf der Synology │
│ (nginx, :8080) │ ◄───────────────────── │    (:8000)     │ ◄───── │ (:3307)          │
└────────────────┘         JSON           └────────────────┘        └──────────────────┘
```

Zwei Container über Docker Compose — **die Datenbank läuft nicht im Stack**:
einzige DB ist die MariaDB auf der Synology, sowohl lokal als auch im
NAS-Deployment (Nutzerentscheidung 2026-07-28). Das Frontend wird als
statisches Build von nginx ausgeliefert; nginx proxied `/api` und `/health` an das
Backend, dadurch braucht der Browser nur einen Origin (kein CORS im Produktivbetrieb;
für den Vite-Dev-Server übernimmt dessen Proxy dieselbe Rolle).

## Verzeichnisstruktur

```
backend/
  app/
    core/config.py     Pydantic-Settings (Env-Präfix VOLLEYSCOUT_, .env-Support)
    db/                SQLAlchemy-Engine/Session (base.py, session.py)
    models/            ORM-Entitäten (siehe docs/DATENBANK.md)
    schemas/           Pydantic-Request-/Response-Modelle
    engine/            Spiellogik (DB-frei, siehe unten)
    api/               FastAPI-Router: teams, matches, live
    main.py            App-Factory, CORS, Router-Registrierung, /health
  alembic/             Migrationen (laufen beim Container-Start automatisch)
  tests/               pytest (Engine, Parser, API über SQLite in-memory)
  Dockerfile, docker-entrypoint.sh, pyproject.toml
frontend/
  src/
    api.js             zentraler Fetch-Wrapper für alle Backend-Aufrufe
    router/            Vue-Router (History-Mode)
    views/             TeamsView, MatchesView, LiveScoutView
    styles.css         globales Styling (kein CSS-Framework)
  Dockerfile (Node-Build-Stage → nginx), nginx.conf, vite.config.js
docker-compose.yml            lokaler Stack (baut selbst; DB = Synology-MariaDB)
docker-compose.synology.yml   NAS-Stack (fertige GHCR-Images; DB = Synology-MariaDB)
.github/workflows/            CI: Image-Build & Push nach GHCR (amd64+arm64)
.env(.example)
docs/                  diese Doku + ROADMAP.md + DVW-FORMAT.md + DEPLOYMENT-SYNOLOGY.md
```

## Kernkonzept: Event-Sourcing fürs Live-Scouting

Quelle der Wahrheit ist die Tabelle `live_events` (siehe `docs/DATENBANK.md`).
Jede Scouting-Eingabe ist ein Event mit fortlaufender `seq` pro Match:

| Event-Typ      | Payload                                              |
|----------------|------------------------------------------------------|
| `start_set`    | `serving`, `home_lineup[6]`, `away_lineup[6]`        |
| `rally`        | `winner`, `actions[]` (geparste Scout-Codes)         |
| `substitution` | `side`, `player_out`, `player_in`                    |
| `timeout`      | `side`                                               |

Ablauf pro Request (`backend/app/api/live.py`):

1. Alle Events des Matches laden (nach `seq` sortiert).
2. `MatchEngine.replay(rules, events)` — Zustand deterministisch rekonstruieren.
3. Neues Event mit `apply_event` gegen die Volleyball-Regeln validieren
   (`RuleViolation` → HTTP 422, **nichts** wird gespeichert).
4. Erst bei Erfolg das Event persistieren und den neuen Zustand zurückgeben.

**Undo** löscht das letzte Event und rekonstruiert per Replay — identisch zum
„Undo End Rally" im DataVolley-Vorbild. Konsequenzen dieses Designs:

- Autosave gratis: jede Eingabe ist sofort persistiert, ein Absturz kostet nichts.
- Der Zustand ist jederzeit reproduzierbar; abgeleitete Tabellen (`rallies`,
  `scout_actions` für den Statistik-Strang, Roadmap 1.2) können später aus dem
  Event-Log erzeugt werden, ohne das Live-Scouting anzufassen.
- Die Engine bleibt eine reine Python-Klasse ohne DB-Abhängigkeit und ist damit
  vollständig unit-testbar (`tests/test_engine.py`).

Rebuild-Kosten: O(Events) pro Request — bei ein paar hundert Events pro Match
unkritisch; bei Bedarf später durch Snapshotting optimierbar.

## Match-Engine (`app/engine/match_engine.py`)

Abgebildete Volleyball-Regeln (Indoor, über `Rules` parametrisierbar — auch Beach
oder Sonderformate möglich):

- **Best-of-N** (Default 5): Matchende bei ⌈N/2⌉ Satzgewinnen; danach werden
  weitere Events abgelehnt.
- **Satzende**: 25 Punkte (Entscheidungssatz: 15) mit mindestens 2 Punkten
  Vorsprung, beides konfigurierbar.
- **Side-Out & Rotation**: gewinnt das annehmende Team den Ballwechsel, bekommt es
  das Aufschlagrecht und rotiert im Uhrzeigersinn (Zone-2-Spieler geht zum
  Aufschlag in Zone 1). Lineup-Repräsentation: Liste `[Zone1, Zone2, …, Zone6]`,
  Rotation = Links-Shift.
- **Wechsel**: Limit pro Satz/Team (Default 6); validiert, dass der ausgewechselte
  Spieler auf dem Feld und der eingewechselte nicht auf dem Feld steht.
- **Auszeiten**: Limit pro Satz/Team (Default 2).
- **Aufstellungen**: exakt 6 eindeutige Spielernummern pro Team.

Bewusst noch **nicht** abgebildet (spätere Versionen): Libero-Tauschlogik,
Rückwechsel-Regel (Spieler darf nur auf seine Position zurück), Setter-Tracking
(`*z`/`az`-Äquivalent), Phasen Side-Out/Break für die Statistik.

## Scout-Code-Parser (`app/engine/scout_code.py`)

Implementiert den DataVolley-**Main-Code** plus optionale Zonen:
`[*|a]<Nummer><Skill><Typ?><Bewertung?><Startzone?><Endzone?>` — z. B. `5SQ=`,
`a7AT#`, `14AH+45`. Kleinschreibung wird normalisiert, unbekannte Restzeichen
bleiben im Rohcode erhalten. Advanced-/Extended-/Compound-Codes folgen laut
Roadmap; vollständige Referenz in der DV4-Tiefenrecherche
(`../recherche/Data_Volley_4_Funktionsanalyse.md`, außerhalb des Repos).

## Konfiguration

`app/core/config.py` (pydantic-settings, Env-Präfix `VOLLEYSCOUT_`):

| Variable                   | Default                                      | Zweck                     |
|----------------------------|----------------------------------------------|---------------------------|
| `VOLLEYSCOUT_DATABASE_URL` | `mysql+pymysql://scout:scout@localhost:3306/volleyscout?charset=utf8mb4` | SQLAlchemy-URL |
| `VOLLEYSCOUT_CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:8080"]` | Dev-CORS |
| `VOLLEYSCOUT_API_PREFIX`   | `/api`                                       | Router-Präfix             |

Beide Compose-Files setzen `VOLLEYSCOUT_DATABASE_URL` aus den
`SYNOLOGY_DB_*`-Variablen der `.env` (git-ignoriert; Vorlage `.env.example`).
Weitere `.env`-Abschnitte:
`SYNOLOGY_HOST`/`PUBLIC_DOMAIN` (Zieldomain `volleyball.absosol.myds.me` für den
Reverse Proxy, Roadmap 1.8), `SYNOLOGY_DB_*` (MariaDB auf der NAS — Schema dort
bereits eingespielt, siehe `docs/DATENBANK.md`) und `SYNOLOGY_SHARE_*`
(Dateiablage `volleyball_master` für Scouts u. Ä.).

## Teststrategie

- `tests/test_engine.py` — Regelwerk isoliert (Rotation, 2-Punkte-Abstand,
  Tiebreak, Matchende, Limits, Replay-Determinismus).
- `tests/test_scout_code.py` — Parser-Grenzfälle.
- `tests/test_api.py` — kompletter API-Flow gegen SQLite in-memory
  (Dependency-Override von `get_db`); die echte MariaDB wird nur im
  Compose-Stack getestet.

Ausführen: `cd backend && .venv/bin/python -m pytest`
