# Roadmap

**Aktuelle Version: 1.0** (abgeschlossen 2026-07-27; Teile von 1.4/1.5 wurden vorgezogen, siehe unten).

## Versionsschema

- **1.0** = erste abgeschlossene Funktionalität. Jede weitere abgeschlossene Funktionalität
  erhöht die Version fortlaufend (1.1, 1.2, 1.3, …) — kein thematisches Bündeln, keine Lücken.
- **2.0** kommt erst nach dem **allerersten Livegang auf der Synology**. Bis dahin läuft alles
  unter 1.x, danach beginnt die 2.x-Reihe für alles, was nach dem ersten produktiven Betrieb
  entsteht.
- Scope laut Nutzerentscheidung (2026-07-27): **Analyse bestehender `.dvw`-Dateien und
  Live-Scouting neuer Spiele sind gleichwertige Kernfunktionen**, keine der beiden ist
  nachrangig. Die Versionen unten wechseln sich deshalb zwischen beiden Strängen ab, statt
  einen Strang komplett vor dem anderen abzuschließen.

## Geplante Versionen (Entwurf, nichts begonnen)

### Version 1.0 — Fundament: Datenmodell & lokale Infrastruktur ✅ (2026-07-27)
- [x] Domänenmodell (Match, Team, Player, MatchSet, Rally, ScoutAction + LiveEvent) —
      `backend/app/models/entities.py`; der alte Prototyp-Bestand wurde auf Nutzerwunsch
      komplett entfernt, alles neu aufgebaut
- [x] MariaDB-Schema — Alembic als Migrations-Tooling, Initial-Migration
      `backend/alembic/versions/0001_initial.py`, läuft beim Container-Start automatisch
- [x] Backend-Grundgerüst — **FastAPI** + SQLAlchemy 2 (Nutzerentscheidung 2026-07-27),
      Struktur unter `backend/app/` (api/, engine/, models/, schemas/, core/, db/)
- [x] Docker-Compose **lokal**: Frontend (nginx) + Backend + MariaDB, end-to-end getestet
      (Frontend-Stack: **Vue 3 + Vite**, ebenfalls Nutzerentscheidung 2026-07-27)

### Version 1.1 — DVW-Import (Analyse-Strang, Start)
- [ ] `src/dv_reader.py` zum vollständigen Parser ausbauen (Basis: `protocol/*.json`,
      `../recherche/Data_Volley_4_Funktionsanalyse.md` — Tiefenrecherche mit vollständiger
      Code-Syntax und .dvw-Sektionsreferenz —, `../recherche/DataVolleyMedia_handbook.pdf`,
      `../recherche/dvwin2007_handbook.pdf`; Korrektheit gegen openvolley/pydatavolley
      validieren, „german convention": `B/` ↔ `B=` vertauscht)
- [ ] Import einer einzelnen `.dvw`-Datei in die MariaDB
- [ ] Batch-Import über einen ganzen Ordner (Testquelle lokal: `../volleyscout_2/scoutdata/` —
      **nie einchecken**, siehe DSGVO-Hinweis in `PROGRESS.md`)

### Version 1.2 — Statistik-Auswertung (Analyse-Strang)
- [ ] Spieler-Statistiken (Asse/Aufschlagfehler, Annahme-Positivquote, Angriffseffizienz,
      Blockpunkte) — Vorbild: `volleyscout/stats.py`
- [ ] Team-Statistiken (Side-Out-/Break-Quote, Punktquellen)
- [ ] Rotationsanalyse
- [ ] Erste REST-API-Endpunkte zum Abfragen importierter Matches/Statistiken

### Version 1.3 — Web-Frontend: Match-Browser (Analyse-Strang)
- [ ] Liste importierter Matches
- [ ] Match-Detailansicht (Teams, Sätze, Ergebnis, Statistik-Panel)

### Version 1.4 — Live-Scouting-Engine (Live-Strang, Start) — vorgezogen umgesetzt in 1.0
- [x] Scout-Code-Parser für Direkteingabe (`<Team><Nummer><Skill><Typ?><Bewertung><Zonen?>`) —
      Main-Code umgesetzt in `backend/app/engine/scout_code.py`; Advanced/Extended/Compound
      folgen später. Vollständige Code-Referenz inkl. Normalisierung, Defaults, Compound Codes
      und automatischer Codes (`*z`/`*p`/`*P`/`*c`) in
      `../recherche/Data_Volley_4_Funktionsanalyse.md`, Abschnitt 3;
      Übernahme-Checkliste dort in Abschnitt 8
- [x] Match-Engine: Punkte, Rotation, Sätze/Match, Side-Out, Auszeiten, Wechsel, Undo —
      `backend/app/engine/match_engine.py` (Event-Sourcing über `live_events`,
      Undo = letztes Event löschen), abgedeckt durch `backend/tests/test_engine.py`

### Version 1.5 — Live-Scouting-Frontend — Basis vorgezogen umgesetzt in 1.0
- [ ] Web-UI fürs Live-Scouten: Scoreboard ✅, Rotationsdarstellung beider Felder ✅,
      Direkteingabe (Scout-Codes) ✅, Undo ✅, Auszeit-/Wechsel-Bedienung ✅
      (`frontend/src/views/LiveScoutView.vue`) — **noch offen:** Klickpfad
      (Team → Spieler → Skill → Bewertung)
- [x] Autosave nach jeder Eingabe — architektonisch gelöst: jede Eingabe wird sofort als
      Event in der DB persistiert, der Zustand ist jederzeit per Replay rekonstruierbar

### Version 1.6 — Zeitstempel & DVW-Export
- [ ] Zeitstempel je Aktion (Wanduhrzeit + Zeitcode seit Satzbeginn) — gilt für Import **und**
      Live-Scouting einheitlich, Grundlage für spätere Video-Synchronisation
- [ ] Export im DVW-kompatiblen Stil (Anschlussfähigkeit an bestehende Tools/DataVolley)

### Version 1.7 — Zusammenführung Analyse- & Live-Strang
- [ ] Live-gescoutete Spiele erscheinen in derselben Match-Übersicht/Statistik wie importierte
- [ ] Validierung/Fehlerbehandlung, Protokoll unbekannter/nicht erkannter Codes (Vorbild:
      `unknown_tokens.csv` aus `../volleyscout_2/scout_app/`)

### Version 1.8 — Synology-Deployment-Vorbereitung ✅ (2026-07-28)
- [x] Docker-Compose für Synology — Entscheidung: **Container** (kein NAS-Paket).
      `docker-compose.synology.yml` nutzt fertige GHCR-Images (GitHub-Action
      `.github/workflows/docker-publish.yml` baut amd64+arm64 bei jedem Push) und die
      Synology-eigene MariaDB (bereits angebunden, Schema per Alembic eingespielt 2026-07-27)
- [ ] Backup-Strategie für die Datenbank (bewusst offen — sinnvoll zusammen mit dem
      ersten echten Datenbestand nach dem Livegang)
- [x] Reverse-Proxy/HTTPS-Vorbereitung — **Zieldomain: `volleyball.absosol.myds.me`**
      (Nutzervorgabe 2026-07-27), dokumentiert als DSM-Klickanleitung inkl.
      Let's-Encrypt-Zertifikat
- [x] **Schritt-für-Schritt-Anleitung** `docs/DEPLOYMENT-SYNOLOGY.md` (Nutzerwunsch
      2026-07-27): GHCR-Sichtbarkeit, Projektordner, Container Manager, interner Test,
      Reverse Proxy, Zertifikat, End-to-End-Verifikation, Updates, Troubleshooting

### Version 1.9 — Erster Livegang auf der Synology
- [ ] Deployment durchgeführt, Health-Check, End-to-End live verifiziert

**→ Version 2.0 beginnt erst hier**, mit allem, was nach dem ersten produktiven Betrieb als
Nächstes angegangen wird (noch nicht geplant).

## Hinweis zur Nummerierung

Diese Liste ist ein **Entwurf** zum jetzigen Zeitpunkt (2026-07-27) — Reihenfolge/Schnitt der
Versionen 1.0–1.9 kann sich beim tatsächlichen Zuschnitt noch verschieben, das
**Nummerierungsprinzip** (fortlaufend 1.x bis zum ersten Livegang, danach 2.0) steht aber fest.
Sobald eine Version tatsächlich abgeschlossen ist, wird der Eintrag hier mit `[x]` abgehakt und
in `PROGRESS.md` mit Details zur Umsetzung dokumentiert.
