# Architektur

Stand: Version 2.4 (2026-07-30) — siehe `docs/ROADMAP.md` für den Versionsverlauf

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
    engine/            Spiellogik + Statistik (DB-frei, siehe unten)
    dvw/               DVW-Parser + -Importer (Analyse-Strang, siehe docs/DVW-FORMAT.md)
    api/               FastAPI-Router: auth, teams, matches, live, imports
    cli.py             Verwaltungs-CLI (create-user, via ../create-user.sh)
    main.py            App-Factory, CORS, Router-Registrierung, /health
  alembic/             Migrationen (laufen beim Container-Start automatisch)
  tests/               pytest (Engine, Parser, API über SQLite in-memory)
  Dockerfile, docker-entrypoint.sh, pyproject.toml
frontend/
  src/
    api.js             zentraler Fetch-Wrapper für alle Backend-Aufrufe
    router/            Vue-Router (History-Mode)
    views/             TeamsView, MatchesView, MatchDetailView (Match-Browser), LiveScoutView
    components/        VolleyballCourt (drehbarer Zonen-Helfer, siehe unten)
    styles.css         globales Styling (kein CSS-Framework)
  Dockerfile (Node-Build-Stage → nginx), nginx.conf, vite.config.js
docker-compose.yml     EINE Compose-Datei für lokal und NAS (baut aus dem Quellcode;
                       DB = Synology-MariaDB; Netz "volleynet" mit fester
                       Frontend-IP 172.29.0.10 als DSM-Reverse-Proxy-Ziel)
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

## Statistik-Engine (`app/engine/statistics.py`)

Reine Berechnungslogik (DB-frei, wie `match_engine.py`) über den Analyse-Strang
(`match_sets`/`rallies`/`scout_actions`); die API-Schicht (`app/api/matches.py`,
`GET /{match_id}/statistics`) lädt die Rally-/Aktionsdaten und übergibt sie als
`RallyRow`/`ActionRow`. Kennzahlen (Formeln aus der DV4-Funktionsanalyse):

- **Spieler**: Serve (Tot/Err/Ass), Reception (Tot/Err/Positivquote/Exzellenzquote),
  Attack (Tot/Err/Blocked/Kills/Effizienz), Block (Tot/Punkte).
- **Team**: Side-Out-/Break-Quote, Punktquellen mit `opponent_errors` als
  **Residual** (Gesamtpunkte − Serve − Angriff − Block), exakt wie im DV4-Report.
- **Rotation**: dieselben Kennzahlen gruppiert nach Setterposition (1–6) — dafür
  trägt `Rally.home_setter_position`/`away_setter_position` (Migration 0003) den
  Wert aus dem DVW-Feld `sp_home/guest_setter_pos` (siehe `docs/DVW-FORMAT.md`
  Abschnitt 2.12), vom DVW-Importer direkt aus der die Rally abschließenden
  Scout-Zeile übernommen.

Bewusst **nicht** Teil dieser Version: Live-gescoutete Matches liefern noch keine
Statistik (der Live-Strang schreibt nur `live_events`, die Zusammenführung in den
Analyse-Strang folgt mit Roadmap 2.7); ebenso die DV4-„Noten" (0–10-Gesamtwertung
mit Mindestbeteiligungsquoten) — die konkreten Zähl-/Quotenkennzahlen decken den
Bedarf der Roadmap ab, ohne die zusätzliche Komplexität der Notenformeln.

## Match-Browser (`frontend/src/views/MatchDetailView.vue`)

Route `/matches/:id`, verlinkt von der Matches-Liste über den „Ansehen"-Button
bei `status: finished`. Lädt Match, Sätze (`GET .../sets`), Statistik
(`GET .../statistics`) sowie beide Kader (für Spielernamen neben den
Trikotnummern in der Statistiktabelle) und zeigt Endstand, Satzverlauf,
Team-Kennzahlen (Break-/Side-Out-Quote als Balken, Punktquellen), eine
Spieler-Statistiktabelle je Team und die Rotationsanalyse je Team.

**Wichtig — Übergangszustand vor Roadmap 2.7**: Ein `finished`-Match kann aus
zwei Strängen stammen, die aktuell getrennt sind (siehe „Kernkonzept" oben).
Liefert `GET .../sets` eine leere Liste (live-gescoutetes Match ohne
übernommene Analyse-Daten), zeigt die Seite statt eines leeren/irreführenden
Panels einen Hinweis mit Link zur Live-Ansicht. Sobald 2.7 beide Stränge
zusammenführt, entfällt dieser Sonderfall automatisch (jedes `finished`-Match
hat dann `match_sets`).

Die Matches-Liste selbst verzweigt seit Version 2.3 nach `status`: ein
zuvor bestehender Bug schickte **jedes** Match (auch importierte, `finished`)
in die Live-Scouting-Ansicht, die dort mangels `live_events` fälschlich eine
„Satz starten"-Maske zeigte, statt das importierte Ergebnis anzuzeigen.

## Kaderverwaltung & Zonen-Helfer (Version 2.4)

- **Team-/Spieler-Nachbearbeitung**: `PATCH /api/teams/{id}` und
  `PATCH /api/teams/{id}/players/{id}` ergänzen die bisher fehlende Möglichkeit,
  Teams/Spieler nach der Anlage zu korrigieren (`TeamsView.vue`, Inline-Edit-Modus).
- **Position als Enum** (`PlayerPosition` in `app/schemas/team.py`): `Zuspieler`,
  `Außenangreifer`, `Diagonalangreifer`, `Mittelblocker`, `Libero` (Standard-
  5-Positionen-System) — validiert nur bei neuen Schreibzugriffen (Create/Update);
  die DB-Spalte bleibt ein einfaches `VARCHAR`, bereits gespeicherte Freitext-Werte
  werden beim Lesen nicht geprüft.
- **`is_youth_player`** (Migration `0004`): reine Kennzeichnung für Spieler mit
  besonderem Status (Höher-/Doppelspielrecht-Regelungen der Landesverbände),
  analog zu `is_libero` — keine Regelprüfung in der Engine.
- **`frontend/src/components/VolleyballCourt.vue`**: drehbare Zonen-/Subzonen-
  Referenz für die Live-Scouting-Zoneneingabe (Klick hängt die Zonen-Ziffer an
  die Scout-Code-Zeile an). 9-Zonen-Raster (3×3, je 3×3 m) mit ABCD-Subzonen
  (je 1,5×1,5 m); Zonenlayout `4,3,2 / 7,8,9 / 5,6,1` (Netzreihe/Mitte/Grundlinie)
  und die Subzonen-Eckzuordnung (A=unten-rechts, B=oben-rechts, C=oben-links,
  D=unten-links, im Uhrzeigersinn) sind gegen die Referenzimplementierung
  `openvolley/datavolley` (R-Paket, Funktion `dv_xy()` in `R/plot.R`) verifiziert.
  Die Drehung ist ein reiner CSS-Transform (`rotate(180deg)` auf das Grid, mit
  gegenläufiger Rotation der Zellbeschriftung) — dieselbe kanonische Datenstruktur
  ergibt dadurch exakt das (punktgespiegelte) Zonenraster der Gegenfeldseite, ohne
  eine zweite Tabelle pflegen zu müssen.
- Bewusst **kein** vollständiger Klickpfad-Ersatz (bleibt Roadmap 2.5): der
  Zonen-Helfer hängt nur die rohe Zonen-Ziffer an, ohne Skill/Bewertung/Spieler
  strukturiert abzufragen.

## Konfiguration

`app/core/config.py` (pydantic-settings, Env-Präfix `VOLLEYSCOUT_`):

| Variable                   | Default                                      | Zweck                     |
|----------------------------|----------------------------------------------|---------------------------|
| `VOLLEYSCOUT_DATABASE_URL` | `mysql+pymysql://scout:scout@localhost:3306/volleyscout?charset=utf8mb4` | SQLAlchemy-URL |
| `VOLLEYSCOUT_CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:8080"]` | Dev-CORS |
| `VOLLEYSCOUT_API_PREFIX`   | `/api`                                       | Router-Präfix             |
| `VOLLEYSCOUT_SECRET_KEY`   | `dev-insecure-change-me`                     | signiert Session-Tokens — in Produktion Pflicht (`openssl rand -hex 32`) |
| `VOLLEYSCOUT_COOKIE_SECURE`| `false`                                      | `true` hinter HTTPS (Reverse Proxy) |
| `VOLLEYSCOUT_SESSION_TTL_HOURS` | `168` (7 Tage)                          | Session-Lebensdauer       |

Die Compose-Datei setzt `VOLLEYSCOUT_DATABASE_URL` aus den
`SYNOLOGY_DB_*`-Variablen der `.env` (git-ignoriert; Vorlage `.env.example`).
Weitere `.env`-Abschnitte:
`SYNOLOGY_HOST`/`PUBLIC_DOMAIN` (Zieldomain `volleyball.<ddns-domain>.myds.me` für den
Reverse Proxy, Roadmap 1.8), `SYNOLOGY_DB_*` (MariaDB auf der NAS — Schema dort
bereits eingespielt, siehe `docs/DATENBANK.md`) und `SYNOLOGY_SHARE_*`
(Dateiablage `volleyball_master` für Scouts u. Ä.).

## Authentifizierung

Muster wie im yugioh_database-Projekt: **Login-Pflicht ohne Registrierung**,
Benutzerverwaltung über `./create-user.sh`, Rollen `admin`/`viewer` (viewer =
jede Schreibroute liefert 403). Technik: PBKDF2-Passwort-Hashes und
HMAC-signierte Session-Tokens im HttpOnly-Cookie (`app/core/security.py` —
bewusst ohne Zusatzabhängigkeiten), Durchsetzung über FastAPI-Dependencies
(`app/api/deps.py`: `get_current_user` auf allen Fachroutern,
`require_writer` auf jeder Schreibroute). Frontend: `LoginView`, zentrales
401-Handling in `src/api.js` (Redirect auf `/login`), Nutzer/Abmelden in der
Navigation.

## Teststrategie

- `tests/test_engine.py` — Regelwerk isoliert (Rotation, 2-Punkte-Abstand,
  Tiebreak, Matchende, Limits, Replay-Determinismus).
- `tests/test_scout_code.py` — Parser-Grenzfälle.
- `tests/test_dvw_import.py` — DVW-Parser (Sample-Datei) + Import-Endpunkt.
- `tests/test_statistics.py` — Statistik-Formeln isoliert (Spieler/Team/
  Rotation) sowie der `GET /matches/{id}/statistics`-Endpunkt nach Import.
- `tests/test_auth.py` — Login/Logout, Rollenprüfung.
- `tests/test_api.py` — kompletter API-Flow gegen SQLite in-memory
  (Dependency-Override von `get_db`); die echte MariaDB wird nur im
  Compose-Stack getestet.

Ausführen: `cd backend && .venv/bin/python -m pytest`
