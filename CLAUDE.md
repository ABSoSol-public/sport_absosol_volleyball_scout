# CLAUDE.md

Konventionen für KI-Sessions (Claude Code oder vergleichbare Tools), die an
diesem Repo arbeiten. Für die Architektur/API/Datenbank selbst: siehe
`README.md`s Doku-Liste (`docs/ARCHITEKTUR.md`, `docs/API.md`,
`docs/DATENBANK.md`, `docs/SPIELFORMATE.md`, `docs/SPIELERPROFILE.md`,
`docs/DVW-FORMAT.md`). Dieses Dokument ist **Prozess**, nicht Substanz.

## Jede substantielle Entscheidung dokumentieren — mit Nutzerzitat

Dieses Projekt hält an vielen Stellen fest, *warum* Code so aussieht, wie er
aussieht — nicht nur *was* er tut. Konkret:

- **Jede neue fachliche Anfrage** (Feature, Regeländerung, Bugfix mit
  Design-Entscheidung) bekommt einen Eintrag in `docs/ENTSCHEIDUNGEN.md`:
  das **wörtliche** Nutzerzitat (keine Paraphrase), was daraus entschieden/
  abgegrenzt wurde, und ein Verweis auf Commit + das betroffene Fach-Dokument.
- **Wenn die KI selbst etwas vorschlägt** und der Nutzer nur zustimmt
  („weiter bitte", „ja", „gerne") statt eine eigene Anforderung zu nennen:
  das explizit so vermerken, nicht so tun, als hätte der Nutzer das Feature
  selbst spezifiziert. Beispiel: `docs/ENTSCHEIDUNGEN.md` Eintrag 2026-09-26 #3.
- **Im Code/den Fach-Docs** (nicht nur im Protokoll): Kommentare/Docstrings,
  die eine nicht offensichtliche Entscheidung begründen, zitieren die
  Nutzervorgabe als `Nutzerwunsch: „…"` bzw. `Nutzerentscheidung: …` — Dutzende
  Beispiele in `docs/ARCHITEKTUR.md` und den anderen `docs/*.md`.
- **Bewusste Lücken/Vereinfachungen explizit benennen**, nicht stillschweigend
  weglassen — Muster: „Bewusst **nicht** abgebildet: … (Begründung)". Beispiel:
  Libero-Skill-Beschränkungen in `docs/ARCHITEKTUR.md`, Jugend-Sonderregeln in
  `docs/SPIELFORMATE.md`.

## Recherche statt Annahme, mit Quellenangabe

Wo Regeln/Fakten von außerhalb des Repos einfließen (Volleyball-Regelwerke,
Dateiformate, Drittanbieter-Verhalten), **vor der Umsetzung recherchieren**
(Web-Suche) und die Quelle im Fach-Dokument verlinken statt aus dem
Trainingswissen zu behaupten. Wenn Quellen uneinheitlich/regional
unterschiedlich sind (z. B. deutsche Jugend-Kleinfeldformen, siehe
`docs/SPIELFORMATE.md`), das explizit als Unsicherheit kennzeichnen statt
falsche Präzision vorzutäuschen.

## Architekturprinzipien, die nicht stillschweigend gebrochen werden sollten

- **`app/engine/*` bleibt DB-frei** (reine Dataclasses/Funktionen, testbar
  ohne Datenbank). DB-anbindende Orchestrierung gehört auf Modulebene
  daneben (`app/analyse_sync.py`, `app/player_data.py`, `app/player_card.py`,
  `app/seasons.py`) oder in `app/api/*`.
- **Ein physischer Spieler = `(team_id, Trikotnummer)`**, keine `player_id`-FK
  in `scout_actions`/`live_events`-Payloads. Konsistent im DVW-Export/-Import
  UND in den Spielerprofilen — nicht durchbrechen, ohne beide Seiten
  anzupassen.
- **Event-Sourcing fürs Live-Scouting bleibt Quelle der Wahrheit**
  (`live_events`); der Analyse-Strang (`match_sets`/`rallies`/
  `scout_actions`) ist eine daraus abgeleitete Kopie (`sync_from_live_events`),
  nie umgekehrt.
- **Kein CSS-Framework, keine neue Chart-Bibliothek im Frontend** — bestehende
  Klassen wiederverwenden (`.card`, `.meter`/`.meter-row`, `.compact`/
  `.stat-table`, `.badge`).
- **Neue Regeln/Formate**: erst prüfen, ob `Rules`/`MatchEngine` sie durch
  vorhandene Parameter bereits abdecken (war z. B. bei `players_on_court` für
  die Mehrfach-Formate der Fall), bevor neue Sonderfälle eingebaut werden.

## Vor jedem Commit

- Backend: `cd backend && .venv/bin/python -m pytest` — muss grün sein (Stand
  2026-09-26: 103 Tests). Neue Engine-Logik bekommt sowohl einen reinen
  Engine-Test als auch einen API-Integrationstest (Konvention aus
  `tests/test_engine.py` + `tests/test_libero.py`/`tests/test_disciplines.py`).
- Frontend: `cd frontend && npm run build` — muss ohne Fehler durchlaufen.
- Bei Frontend-Änderungen mit Nutzerinteraktion: wenn möglich, per
  Playwright (Chromium unter `/opt/pw-browsers`, siehe Session-Notizen) real
  durchklicken, nicht nur den Build prüfen.
- Migrationen (`backend/alembic/versions/`) laufen nur gegen echtes MariaDB
  zuverlässig durch (SQLite kennt kein `ALTER COLUMN … DROP DEFAULT`) — die
  Testsuite umgeht das über `Base.metadata.create_all`. Neue Migrationen also
  nicht per SQLite-Testlauf verifizieren, sondern gegen das bestehende Muster
  in `alembic/versions/000*.py` prüfen.

## Git-Workflow dieser Session

Nutzerentscheidung 2026-09-26 („nene gleich in master rein, fertig aus"):
Commits gehen direkt auf den Arbeitsbranch **und** `master`, kein Pull
Request. Gilt, bis der Nutzer das ändert — bei Unsicherheit lieber
nachfragen als stillschweigend auf PR-Workflow zurückfallen oder umgekehrt.
