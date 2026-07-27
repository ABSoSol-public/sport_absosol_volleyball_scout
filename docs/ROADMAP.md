# Roadmap

**Aktuelle Version: 1.9 — die App ist live auf der Synology** (`https://volleyball.<ddns-domain>.myds.me`, seit 2026-07-28).
Umgesetzt: 1.0 (Fundament), 1.4 (Live-Engine), Basis von 1.5 (Live-Frontend), 1.8/1.9 (Deployment).
Noch offen aus der 1.x-Planung (werden als 2.x weitergeführt): 1.1–1.3 (Analyse-Strang), Rest von 1.5, 1.6, 1.7.

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
- [x] Docker-Compose für Synology — Entscheidung (revidiert auf Nutzerwunsch, 2026-07-28):
      **gleiches Muster wie `yugioh_database`** — Quellcode per `git clone` auf die NAS,
      dort `docker-compose --env-file .env up -d --build`; EINE Compose-Datei für lokal
      und NAS, DB ist die Synology-MariaDB (Schema per Alembic eingespielt 2026-07-27).
      Der zwischenzeitliche GHCR-Image-Ansatz (GitHub-Action + separates Synology-Compose)
      wurde wieder entfernt (Git-History `b7f6c92`)
- [ ] Backup-Strategie für die Datenbank (bewusst offen — sinnvoll zusammen mit dem
      ersten echten Datenbestand nach dem Livegang)
- [x] Reverse-Proxy/HTTPS-Vorbereitung — **Zieldomain: `volleyball.<ddns-domain>.myds.me`**
      (Nutzervorgabe 2026-07-27), dokumentiert als DSM-Klickanleitung inkl.
      Let's-Encrypt-Zertifikat
- [x] **Schritt-für-Schritt-Anleitung** `docs/DEPLOYMENT-SYNOLOGY.md` (Nutzerwunsch
      2026-07-27): GHCR-Sichtbarkeit, Projektordner, Container Manager, interner Test,
      Reverse Proxy, Zertifikat, End-to-End-Verifikation, Updates, Troubleshooting

### Version 1.9 — Erster Livegang auf der Synology ✅ (2026-07-28)
- [x] Deployment durchgeführt, Health-Check, End-to-End live verifiziert —
      die App läuft unter **https://volleyball.<ddns-domain>.myds.me** (Let's-Encrypt-Zertifikat
      gültig bis Okt. 2026, Reverse Proxy auf 172.29.0.10:80, parallel zum tcg-Stack).
      Ablauf: Nutzer hat geclont + gebaut + DSM-Schritte geklickt; `.env`, Vorprüfungen
      und Verifikation liefen per SSH (siehe `PROGRESS.md`)

**→ Die 2.x-Reihe beginnt hier**: alles Weitere (offene 1.x-Reste wie DVW-Import 1.1,
Statistik 1.2, Match-Browser 1.3, Klickpfad 1.5, Zeitstempel/Export 1.6, Zusammenführung 1.7
sowie Backup-Strategie aus 1.8) wird ab jetzt als 2.x nummeriert bzw. neu zugeschnitten.

## Hinweis zur Nummerierung

Diese Liste ist ein **Entwurf** zum jetzigen Zeitpunkt (2026-07-27) — Reihenfolge/Schnitt der
Versionen 1.0–1.9 kann sich beim tatsächlichen Zuschnitt noch verschieben, das
**Nummerierungsprinzip** (fortlaufend 1.x bis zum ersten Livegang, danach 2.0) steht aber fest.
Sobald eine Version tatsächlich abgeschlossen ist, wird der Eintrag hier mit `[x]` abgehakt und
in `PROGRESS.md` mit Details zur Umsetzung dokumentiert.
