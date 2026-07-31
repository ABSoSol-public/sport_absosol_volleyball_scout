# Architektur

Stand: Version 2.4–2.5 (2026-07-31, laufend) — siehe `docs/ROADMAP.md` für den Versionsverlauf

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
    components/        VolleyballCourt (Zonen-/Richtungs-Helfer), RotationCourt
                       (Rotationsanzeige, siehe unten)
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

## Kaderverwaltung, Zonen-Helfer & Richtung (Version 2.4–2.5)

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
- **`frontend/src/components/VolleyballCourt.vue`**: Zonen-/Subzonen-Referenz für
  die Live-Scouting-Zoneneingabe, als **vollständiges Feld** (beide Hälften +
  Netz gleichzeitig sichtbar, damit es im Live-Betrieb schnell geht — keine
  Dreh-Bedienung nötig). 9-Zonen-Raster (3×3, je 3×3 m) mit ABCD-Subzonen
  (je 1,5×1,5 m) je Hälfte; Zonenlayout `4,3,2 / 7,8,9 / 5,6,1`
  (Netzreihe/Mitte/Grundlinie) und die Subzonen-Eckzuordnung (A=unten-rechts,
  B=oben-rechts, C=oben-links, D=unten-links, im Uhrzeigersinn) sind gegen die
  Referenzimplementierung `openvolley/datavolley` (R-Paket, Funktion `dv_xy()`
  in `R/plot.R`) verifiziert. Die Gastfeld-Hälfte ist **dieselbe** kanonische
  Zellliste wie die Heimfeld-Hälfte, nur per CSS `rotate(180deg)` auf den
  Container gedreht (Zellbeschriftung wird pro Zelle gegenläufig zurückgedreht,
  damit der Text aufrecht bleibt) — ergibt automatisch das punktgespiegelte
  Zonenraster der Gegenseite, ohne eine zweite Tabelle zu pflegen. Optische
  Anlehnung an ein echtes Feld: Netzleiste zwischen den Hälften, durchgezogene
  weiße Linie an der echten 3-Meter-/Angriffslinie (Grenze Netzreihe/Mittelreihe),
  die übrigen Zonengrenzen nur gestrichelt (keine echten Feldlinien).
- Klick-Reihenfolge rückt automatisch weiter: erster Klick = Startzone, zweiter
  = Zielzone + Subzone (Richtung) — bei Bedarf oben manuell umschaltbar (z. B.
  Block ohne Startzone). Start- und Zielzelle bleiben **beide** farblich markiert
  (unterschiedliche Farben), bis eine neue Aktion beginnt — der zweite Klick
  ändert/löscht die Startzonen-Markierung nicht. Ein Pfeil (SVG-Overlay über dem
  Feld) verbindet Start- und Zielzelle, sobald beide gesetzt sind; die Position
  wird beim Klick direkt aus der gerenderten Zellen-/Feld-Geometrie gemessen
  (`getBoundingClientRect`, als Prozent relativ zum Feld gespeichert), nicht aus
  dem Zonenraster errechnet — dadurch unabhängig von der Netzleisten-Höhe (fix
  in rem) gegenüber den quadratischen, mitskalierenden Feldhälften. Bewusst
  **kein** vollständiger Klickpfad-Ersatz (bleibt Roadmap 2.5): der Zonen-Helfer
  hängt nur Zonen-Ziffer(n) an, ohne Skill/
  Bewertung/Spieler strukturiert abzufragen.
- **Kaderbasierte Aufstellungs-Eingabe** (Roadmap 2.5, Nutzerfeedback nach 2.4):
  die Sätze-starten-Maske in `LiveScoutView.vue` zeigt je Team ein Zonen-Raster
  (gleiches Layout wie die Rotationsanzeige eines laufenden Satzes), jede Zone
  ist ein `<select>` mit dem Kader des Teams statt einer Freitext-Nummernliste;
  Duplikat-Zuordnung wird clientseitig als Hinweis angezeigt (die Engine
  validiert serverseitig ohnehin). Ebenso die Wechsel-Auswahl: „Raus" listet nur
  die laut `current_set.lineups` aktuell auf dem Feld stehenden Spieler, „Rein"
  nur den Rest des Kaders. Liberos sind mit „(L)" markiert. `MatchEngine.state()`
  liefert seit dieser Version je `set_scores`-Eintrag zusätzlich `lineups`
  (Endaufstellung des Satzes) — das Frontend schlägt daraus die Aufstellung für
  den nächsten Satz vor, auch nach einem Seiten-Reload (analog zum DV4-Verhalten
  „ab Satz 2 wird das vorherige LineUp vorgeschlagen").
- **`frontend/src/components/RotationCourt.vue`** (Roadmap 2.5, Nutzerwunsch
  „Volleyballfeld mit den aktuellen Rotationen, wo stehen die Spieler"): ersetzt
  die schlichten Zonen-Boxen der laufenden-Satz-Anzeige durch ein echtes Feld im
  selben Stil wie `VolleyballCourt.vue` (Netzleiste, Sandfarbe), aber mit dem
  einfachen 6-Zonen-Rotationsraster (Netzreihe 4-3-2 im 3-m-Band, Grundlinie
  5-6-1 im 6-m-Band — Zeilenhöhe deshalb bewusst 1:2 statt 1:1) statt der 36
  Subzonen-Zellen. Zwei unabhängige Anzeige-Steuerungen, nach DV4-Vorbild
  (`ROT`/`INV`-Befehle im Command Window, siehe Recherche Abschnitt 4.2):
  „90° drehen" schaltet zwischen horizontaler und vertikaler Netzausrichtung um
  (für Scouts, die seitlich statt hinter der Grundlinie sitzen) — die vertikale
  Zellzuordnung ist eine per Matrixformel abgeleitete 90°-Rotation des
  horizontalen Rasters, nicht von Hand geschätzt; „Seitenwechsel" vertauscht,
  welches Team auf welcher Seite angezeigt wird, unabhängig von der Ausrichtung.
  Liberos sind mit einem „L"-Badge markiert (aus dem geladenen Kader). Aufschlag
  wird mit demselben `.serve-dot` wie im Scoreboard markiert.
  **Editierbar**: ein „Aufstellung korrigieren"-Modus macht jede Zone zu einem
  Kader-`<select>`; Speichern ruft `POST .../live/lineup-correction` auf (neuer
  Event-Typ `correct_lineup` in `match_engine.py`) — überschreibt die Aufstellung
  direkt, unabhängig vom regulären Wechsel-Event und **ohne** das Wechsellimit zu
  belasten, gedacht für Erfassungsfehler (z. B. verpasste Rotation), nicht für
  echte Spielzüge. Setter-Markierung (im DV4-Vorbild eine eigene Farbe) bewusst
  nicht umgesetzt, da die Engine noch kein Setter-Tracking kennt (Roadmap 2.8).
- **Richtungserfassung (Subzone) & Kombinationscodes** (Roadmap 2.5, Nutzerwunsch
  „lerne aus dem Web, wie DataVolley das macht"): Subzone ist die eigentliche
  Richtungsangabe (Startzone → Zielzone+Subzone) und wird jetzt an beiden Enden
  erfasst — Live-Direkteingabe (`app/engine/scout_code.py`, `ParsedAction.subzone`,
  z. B. `14AH+45B`) und DVW-Import (`app/dvw/parser.py`, `DvwScoutRow.
  attack_combination`/`target_attack`/`subzone` aus dem Advanced Code, Migration
  `0005` auf `scout_actions`). `VolleyballCourt.vue` liefert dafür Zone+Subzone
  UND ob der Klick gerade als Start- oder Zielzone gemeint war (`target`,
  automatisch fortschreitend) — vorher war die Subzone im Helfer rein dekorativ.
  Angriffskombinations-/Setter-Call-Codes (Advanced-Code-
  Feld 7–8, Grundlage für Zuspielverteilung-Analysen) werden beim **Import**
  miterfasst, aber bewusst **nicht** in die kompakte Live-Direkteingabe
  aufgenommen (dort mehrdeutig ohne Trennzeichen zur nachfolgenden Zone) — das
  wäre erst mit einer strukturierten Eingabe (Klickpfad, Roadmap 2.5 Rest-Punkt)
  sauber lösbar.
- **Rotations-Gleichstand & UI-Vereinheitlichung** (Roadmap 2.5, Nutzerfeedback
  nach dem Dogfooding von RotationCourt: „beim Drehen skaliert das Feld zu
  klein, Zonen-Helfer muss auch drehen können, 2 Reiter ist UI-seitig
  ungeschickt"):
  - **`frontend/src/lib/court-grid.js`**: neue `transpose()`-Utility
    (Matrix-Transponierung), von beiden Feld-Komponenten geteilt genutzt, um
    das vertikale Zonenraster aus dem horizontalen abzuleiten statt eine
    zweite Tabelle von Hand zu pflegen. Empirisch gegen den gerenderten
    RotationCourt verifiziert (nicht die zunächst versuchte Rotationsformel —
    die lieferte zweimal ein falsches Ergebnis, die Transponierung war die
    tatsächlich passende Transformation).
  - **Skalierungs-Fix**: beide Feld-Komponenten hatten einen statischen
    `max-width`-Wert (für die horizontale Ausrichtung bemessen), der die
    vertikale Ausrichtung (braucht etwa die doppelte Breite) unnötig
    zusammenquetschte. Erster Versuch (nur `max-width` dynamisch an `vertical`
    gebunden) reichte nicht: `max-width` ist nur eine Obergrenze, erzwingt aber
    keine tatsächliche Breite — die umgebende Flex-/Grid-Kette blieb
    Inhaltsgröße-bestimmt (shrink-to-fit) und das Feld landete trotzdem beim
    kleinen Inhalts-Minimum. Tatsächlicher Fix: eine feste `width` (statt nur
    `max-width`) je Ausrichtung binden (`RotationCourt.vue` 20rem/38rem,
    `VolleyballCourt.vue` 18rem/34rem, zusätzlich `max-width:100%` als
    Sicherheitsnetz gegen schmale Viewports) plus `flex:1` auf dem
    Feldhälften-Grid im rotierten (Reihen-)Layout, damit es die durch die feste
    Breite verfügbare Fläche auch tatsächlich ausfüllt statt nur an ihr
    gedeckelt zu sein.
  - **`VolleyballCourt.vue` jetzt gleichwertig zum Rotationshelfer drehbar**:
    gleicher „⟳ 90° drehen"-Button, `activeGrid = transpose(cells)` im
    vertikalen Modus. Da die Grenzlinien (echte Angriffslinie vs. reine
    Auswertungs-Hilfslinien) beim Transponieren die Seite wechseln, übernimmt
    eine neue `cellLineStyle(cell)`-Funktion das Mapping: was horizontal
    `border-bottom` war (Zeilengrenze zwischen Zonen-Reihen: Angriffslinie
    und Zonen-Hilfslinie) wird vertikal zu `border-right`, was horizontal
    `border-right` war (Spaltengrenze zwischen Zonen-Spalten) wird vertikal
    zu `border-bottom` — rechnerisch anhand der transponierten Zellindizes
    hergeleitet, nicht geschätzt.
  - **`LiveScoutView.vue`**: das bisherige Nebeneinander aus immer sichtbarem
    RotationCourt + eingeklapptem `<details>` für VolleyballCourt (wirkte
    inkonsistent) ist einem `.field-helpers`-Flex-Container gewichen, der
    **beide** Feld-Komponenten gleichzeitig nebeneinander zeigt (kein Klick
    nötig, um zwischen ihnen zu wechseln — erster Entwurf hatte hier
    stattdessen Tabs, per Nutzerfeedback direkt danach durch echtes
    Nebeneinander ersetzt, siehe unten). `flex-wrap: wrap` lässt die beiden
    Karten bei schmalen Viewports oder wenn beide gleichzeitig in den
    vertikalen (breiteren) Modus gedreht sind, untereinander statt
    nebeneinander landen — bewusst als Responsive-Fallback, kein Bug. Der
    lange Erklärungstext unter dem Zonen-Helfer bekam eine eigene
    `max-width` (`.court-selection-hint`), da sein ungewrappter Text sonst die
    bevorzugte (intrinsische) Breite der ganzen Karte aufbläht und das
    Nebeneinander verhindert. Die jetzt ungenutzten `details.card`-CSS-Regeln
    in `styles.css` wurden durch `.field-helpers`/`.field-helper` ersetzt.

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
