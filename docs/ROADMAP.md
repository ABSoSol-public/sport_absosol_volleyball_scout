# Roadmap

**Aktuelle Version: 2.4** — die App ist live auf der Synology (seit 2026-07-28, Domain siehe
lokale `.env`), mit Login-Pflicht (2.0), DVW-Import (2.1), Statistik-Auswertung (2.2),
Match-Browser (2.3) und Kaderverwaltung/Zonen-Helfer (2.4). Nächste geplante Version:
**2.5 Klickpfad-Eingabe**.

## Versionsschema

- Jede **abgeschlossene Funktionalität** erhöht die Version fortlaufend — kein thematisches
  Bündeln, keine Lücken. Die 1.x-Reihe endete mit dem **ersten Livegang auf der Synology**
  (1.9); seitdem läuft die 2.x-Reihe.
- Scope laut Nutzerentscheidung (2026-07-27): **Analyse bestehender `.dvw`-Dateien und
  Live-Scouting neuer Spiele sind gleichwertige Kernfunktionen** — die Versionen wechseln
  zwischen beiden Strängen, statt einen Strang komplett vor dem anderen abzuschließen.
- Abgeschlossene Versionen werden hier abgehakt; Umsetzungsdetails stehen im lokalen
  Session-Log (`PROGRESS.md`, nicht versioniert).

## Umgesetzte Versionen

### 1.0 — Fundament: Datenmodell & lokale Infrastruktur ✅ (2026-07-27)
- [x] Domänenmodell (Match, Team, Player, MatchSet, Rally, ScoutAction + LiveEvent) —
      `backend/app/models/entities.py`; der alte Prototyp-Bestand wurde auf Nutzerwunsch
      komplett entfernt, alles neu aufgebaut
- [x] MariaDB-Schema — Alembic als Migrations-Tooling (`backend/alembic/`), Migrationen
      laufen beim Container-Start automatisch
- [x] Backend-Grundgerüst — **FastAPI** + SQLAlchemy 2 (Nutzerentscheidung 2026-07-27),
      Struktur unter `backend/app/` (api/, engine/, dvw/, models/, schemas/, core/, db/)
- [x] Docker-Compose lokal, end-to-end getestet (Frontend: **Vue 3 + Vite**, ebenfalls
      Nutzerentscheidung 2026-07-27)

### 1.4 (vorgezogen in 1.0) — Live-Scouting-Engine ✅
- [x] Scout-Code-Parser für Direkteingabe — Main-Code in `backend/app/engine/scout_code.py`;
      vollständige Code-Referenz in `../recherche/Data_Volley_4_Funktionsanalyse.md`
      (Abschnitt 3, Übernahme-Checkliste Abschnitt 8; liegt außerhalb des Repos)
- [x] Match-Engine: Punkte, Rotation, Sätze/Match, Side-Out, Auszeiten, Wechsel, Undo —
      `backend/app/engine/match_engine.py` (Event-Sourcing über `live_events`)

### 1.5 (Basis, vorgezogen in 1.0) — Live-Scouting-Frontend ✅ / Rest → 2.4
- [x] Scoreboard, Rotationsdarstellung beider Felder, Scout-Code-Direkteingabe, Undo,
      Auszeit-/Wechsel-Bedienung (`frontend/src/views/LiveScoutView.vue`)
- [x] Autosave nach jeder Eingabe (Event-Persistierung + Replay)

### 1.8 — Synology-Deployment-Vorbereitung ✅ (2026-07-28)
- [x] Deployment-Muster wie `yugioh_database`: `git clone` auf die NAS, dort
      `docker-compose --env-file .env up -d --build`; EINE Compose-Datei für lokal und NAS,
      einzige DB ist die Synology-MariaDB (kein DB-Container)
- [x] Reverse-Proxy/HTTPS als DSM-Klickanleitung inkl. Let's-Encrypt:
      `docs/DEPLOYMENT-SYNOLOGY.md`

### 1.9 — Erster Livegang auf der Synology ✅ (2026-07-28)
- [x] Deployment durchgeführt, Health-Check und End-to-End extern verifiziert
      (gültiges Zertifikat, Reverse Proxy auf feste Container-IP, parallel zum tcg-Stack)

### 2.0 — Login & Rollen ✅ (2026-07-28)
- [x] Login-Pflicht für die gesamte App (öffentlich erreichbar!) — keine Registrierung,
      Benutzerverwaltung über `create-user.sh`, Rollen **admin** / **viewer** (nur lesen),
      HMAC-signierte HttpOnly-Session-Cookies, PBKDF2-Hashes, Migration `0002_users`,
      Login-View + 401-Redirect + Abmelden im Frontend

### 2.1 — DVW-Import (ehem. 1.1, Analyse-Strang) ✅ (2026-07-28)
- [x] DVW-Parser (`backend/app/dvw/parser.py`) nach `docs/DVW-FORMAT.md`: Sektions-Layout,
      positionsbasiertes Tilde-Padding, CP1252-Fallback — **an 120 echten Scoutdateien
      validiert (120/120 fehlerfrei)**
- [x] Einzeldatei-Import `POST /api/imports/dvw` (Upload auf der Matches-Seite):
      Teams/Spieler-Wiederverwendung, Match + Sätze + Ballwechsel + Aktionen in den
      Analyse-Strang (`match_sets`/`rallies`/`scout_actions`)

### 2.2 — Statistik-Auswertung (ehem. 1.2, Analyse-Strang) ✅ (2026-07-29)
- [x] Spieler-Statistiken (Serve Asse/Fehler, Reception Positiv-/Exzellenzquote,
      Angriffseffizienz `(Kills−Err−Blocked)/Tot`, Blockpunkte) —
      `backend/app/engine/statistics.py`, Formeln aus der DV4-Recherche
- [x] Team-Statistiken (Side-Out-/Break-Quote, Punktquellen mit `opponent_errors`
      als Residual: Gesamtpunkte − Serve − Angriff − Block, wie im DV4-Report)
- [x] Rotationsanalyse nach Setterposition (1–6) — DVW-Feld `sp_home/guest_setter_pos`
      wird jetzt geparst und je Ballwechsel auf `Rally.home/away_setter_position`
      übernommen (Migration 0003), da für eine DV4-treue Rotationsanalyse die reine
      Side-Out-Zählung nicht ausreicht (Nutzerentscheidung 2026-07-29: volle
      Setter-Positionen statt vereinfachtem Rotationsindex)
- [x] REST-Endpunkt `GET /api/matches/{id}/statistics` (Spieler/Team/Rotation home+away)

### 2.3 — Match-Browser (ehem. 1.3, Analyse-Strang) ✅ (2026-07-29)
- [x] Match-Detailansicht importierter Spiele (Teams, Sätze, Ergebnis, Statistik-Panel) —
      `frontend/src/views/MatchDetailView.vue`, Route `/matches/:id`; neuer Endpunkt
      `GET /api/matches/{id}/sets`; Fallback-Hinweis mit Link zur Live-Ansicht, falls ein
      `finished`-Match noch keine Analyse-Daten hat (live gescoutet, vor Roadmap 2.7)
- [x] Nebenbei behobenen Bug in der Matches-Liste gefixt: „Ansehen" bei importierten
      Matches landete bisher fälschlich in der Live-Scouting-Ansicht (keine `live_events`
      vorhanden → irreführende „Satz starten"-Maske statt Ergebnis)
- [x] Frontend-Politur (Nutzerwunsch, nicht nur Match-Browser): Hover-/Transition-Feedback
      auf Buttons/Tabellenzeilen/Karten, Badges (Status, Effizienz), Meter-Balken für
      Quoten, Empty-States — `frontend/src/styles.css`

### 2.4 — Kaderverwaltung & Zonen-Helfer (Nutzerfeedback nach 2.3) ✅ (2026-07-30)
- [x] Team/Spieler-Nachbearbeitung: `PATCH /api/teams/{id}` und
      `PATCH /api/teams/{id}/players/{id}` (bisher nur Anlage möglich, keine Korrektur) —
      inline Bearbeiten-Modus in `TeamsView.vue`
- [x] Position vom Freitext- zum Enum-Feld (`Zuspieler`/`Außenangreifer`/
      `Diagonalangreifer`/`Mittelblocker`/`Libero`, Standard-5-Positionen-System,
      webrecherchiert) — nur clientseitig als Dropdown erzwungen, bestehende
      Freitext-Werte in der DB bleiben unangetastet
- [x] Neue Kennzeichnung „Jugendspieler" (`is_youth_player`, Migration `0004`) — reiner
      Marker analog `is_libero`, keine Regelprüfung (echte Höher-/Doppelspielrecht-Logik
      der Landesverbände wäre eigenes Thema, hier bewusst nicht abgebildet)
- [x] Formular-Politur: Labels sauber über den Feldern (`.field`-Klasse) statt nur
      Placeholder-Text, in TeamsView/MatchesView/LiveScoutView/LoginView
- [x] Neue Komponente `frontend/src/components/VolleyballCourt.vue`: drehbares
      9-Zonen-Raster (3×3, je 3×3 m) mit ABCD-Subzonen (je 1,5×1,5 m) für die
      Live-Scouting-Zoneneingabe — Zonenlayout UND die 180°-Beziehung der
      Gegenfeld-Zonen gegen `openvolley/datavolley` (R-Referenzimplementierung,
      `R/plot.R`/`dv_xy()`) verifiziert, deckt sich mit der bereits in `PROGRESS.md`
      dokumentierten Kurzreferenz. **Abweichung gefunden**: die Ecke der Subzone A
      wurde ursprünglich als „unten links" beschrieben, die verifizierte Quelle hat
      A tatsächlich „unten rechts" (im Uhrzeigersinn ab A: A→B→C→D = unten-rechts →
      oben-rechts → oben-links → unten-links) — umgesetzt nach der verifizierten
      Quelle, Konstante zum Umdrehen liegt zentral in der Komponente
- [x] Zonen-Helfer bewusst nur als Referenz-/Klick-Werkzeug (hängt die Zonen-Ziffer an
      die bestehende Scout-Code-Zeile an), **kein** vollständiger Klickpfad-Ersatz —
      das bleibt Umfang von 2.5

## Geplante Versionen

### 2.5 — Klickpfad-Eingabe (Rest von 1.5, Live-Strang)
- [ ] Klickpfad Team → Spieler → Skill → Bewertung als Alternative zur Direkteingabe,
      inkl. UI-Sperrmuster (Bedienelemente erst nach gültiger Vorauswahl freigeben)
- [x] Kaderanbindung: Aufstellungs-Eingabe gegen den hinterlegten Kader validieren
      (inkl. Libero-Kennzeichnung) ✅ (2026-07-30, Nutzerfeedback) — Aufstellung wird
      jetzt per Zonen-Raster mit Kader-Dropdowns gewählt statt Freitext-Nummernliste
      (`LiveScoutView.vue`), Wechsel-Dropdowns ebenfalls kaderbasiert (Feld-/Bank-
      Spieler getrennt), Libero mit „(L)" markiert, vorherige Endaufstellung wird für
      den nächsten Satz vorgeschlagen (`set_scores[].lineups` im Live-Zustand, DV4-
      Vorbild: „ab Satz 2 wird das vorherige LineUp vorgeschlagen")

### 2.6 — Zeitstempel & DVW-Export (ehem. 1.6)
- [ ] Zeitstempel je Aktion (Wanduhrzeit + Zeitcode seit Satzbeginn) für Import und
      Live-Scouting einheitlich — Grundlage für spätere Video-Synchronisation
      (die `live_events` tragen bereits `created_at`, das DVW-Format Feld 7/12)
- [ ] Export im DVW-kompatiblen Stil (Anschlussfähigkeit an DataVolley-Tools)

### 2.7 — Zusammenführung Analyse- & Live-Strang (ehem. 1.7)
- [ ] Live-gescoutete Spiele erscheinen in derselben Match-Übersicht/Statistik wie
      importierte (Ableitung `live_events` → `rallies`/`scout_actions`)
- [ ] Protokoll unbekannter/nicht erkannter Codes beim Import

### 2.8 — Betrieb & Import-Ausbau
- [ ] Backup-Strategie für die Datenbank (Rest aus 1.8 — jetzt relevant, da echte
      Daten entstehen; Vorbild: `backup-db.sh` im yugioh_database-Projekt)
- [ ] DVW-Batch-Import über einen ganzen Ordner (Rest aus 2.1; Testquelle lokal:
      `../volleyscout_2/scoutdata/` — **nie einchecken**, DSGVO)
- [ ] Setter-Tracking & Phasen (Side-Out/Break) in Engine und Statistik
- [ ] Libero-Tauschlogik und Rückwechsel-Regel in der Engine

## Hinweis zur Nummerierung

Reihenfolge/Schnitt der **geplanten** 2.x-Versionen ist Entwurf (Stand 2026-07-28) und kann
sich beim tatsächlichen Zuschnitt verschieben; das Nummerierungsprinzip (fortlaufend, eine
Nummer je abgeschlossener Funktionalität) steht fest. Historie: die ursprüngliche
1.x-Planung (2026-07-27) sah 1.1–1.7 vor dem Livegang vor — durch den vorgezogenen
Livegang wurden 1.1–1.3/1.6/1.7 in die 2.x-Reihe überführt (Zuordnung steht bei den
jeweiligen Versionen).
