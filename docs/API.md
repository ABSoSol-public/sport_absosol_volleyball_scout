# API-Referenz

Stand: Version 2.4 (2026-07-30). Basis-URL: `/api` (im Compose-Stack über das
Frontend erreichbar: `http://localhost:8080/api`, direkt: `http://localhost:8000/api`).
Interaktive OpenAPI-Doku: **`http://localhost:8000/docs`** (immer aktueller als
diese Datei — hier stehen Semantik und Beispiele, dort das generierte Schema).

Alle Bodies sind JSON. Fehlerformat (FastAPI-Standard):

```json
{ "detail": "Wechsellimit erreicht (6 pro Satz)." }
```

| Status | Bedeutung |
|---|---|
| 401 | Nicht angemeldet / Session abgelaufen (alle `/api`-Routen außer `/auth/login`) |
| 403 | Rolle `viewer` versucht eine schreibende Aktion |
| 404 | Ressource nicht gefunden (Team/Match) |
| 409 | Konflikt (Team-Code oder Trikotnummer bereits vergeben) |
| 422 | Validierungsfehler **oder Regelverstoß** der Live-Engine (mit deutscher Meldung) |

---

## Authentifizierung

Alle `/api`-Routen erfordern eine Session (HttpOnly-Cookie `volleyscout_session`,
SameSite=Lax, `Secure` hinter HTTPS); nur `/health` und `/api/auth/login` sind offen.
Es gibt **keine Registrierung** — Benutzer legt `./create-user.sh <name> <pw> [admin|viewer]`
an (bei bestehendem Namen: Passwort-Reset). Rollen: `admin` = Vollzugriff,
`viewer` = nur lesen (jede schreibende Route → 403).

### `POST /api/auth/login`
```json
{ "username": "scout", "password": "…" }
```
→ `{ "username": "scout", "role": "admin" }` + Session-Cookie. Falsche Daten → 401.

### `POST /api/auth/logout`
Löscht das Session-Cookie.

### `GET /api/auth/me`
→ `{ "username": "...", "role": "admin|viewer" }` — für Frontend-Zustand.

---

## Health

### `GET /health`
→ `{ "status": "ok" }` — für Compose-/Synology-Healthchecks.

---

## Teams

### `GET /api/teams`
Liste aller Teams. → `[{ "id": 1, "code": "TSV", "name": "TSV Heimstadt" }, …]`

### `POST /api/teams` → 201
```json
{ "code": "TSV", "name": "TSV Heimstadt" }
```
`code` (max. 8 Zeichen) ist eindeutig → 409 bei Doppelanlage.

### `GET /api/teams/{team_id}`
Team inkl. Kader:
```json
{
  "id": 1, "code": "TSV", "name": "TSV Heimstadt",
  "players": [
    { "id": 3, "number": 7, "last_name": "Musterfrau", "first_name": "Erika",
      "position": "Außenangreifer", "is_libero": false, "is_youth_player": false }
  ]
}
```

### `PATCH /api/teams/{team_id}`
```json
{ "code": "TSV", "name": "TSV Heimstadt e. V." }
```
Beide Felder Pflicht (vollständiger Ersatz, kein Partial-Patch). 409 bei Code-Konflikt
mit einem anderen Team, 404 bei unbekannter `team_id`.

### `POST /api/teams/{team_id}/players` → 201
```json
{ "number": 7, "last_name": "Musterfrau", "first_name": "Erika",
  "position": "Außenangreifer", "is_libero": false, "is_youth_player": false }
```
`number` 0–99, pro Team eindeutig → 409 bei Doppelvergabe. `position` ist optional
(`null`/weggelassen → leer) und eines von: `Zuspieler`, `Außenangreifer`,
`Diagonalangreifer`, `Mittelblocker`, `Libero` — 422 bei anderem Wert. Nur eine
Validierung neuer Einträge; bereits gespeicherte Freitext-Positionen (vor Version 2.4)
bleiben unverändert und werden beim Lesen nicht geprüft.

### `PATCH /api/teams/{team_id}/players/{player_id}`
Gleiches Body-Schema wie beim Anlegen (vollständiger Ersatz). 409 bei Nummern-Konflikt
mit einem anderen Spieler im selben Team, 404 bei unbekannter `team_id`/`player_id`.

---

## Matches

### `GET /api/matches`
Liste (absteigend nach Datum), jede Zeile enthält `home_team`/`away_team` als
eingebettete Team-Objekte sowie den `status` (`scheduled` | `live` | `finished`).

### `POST /api/matches` → 201
```json
{
  "match_date": "2026-07-27",
  "competition": "Oberliga",
  "home_team_id": 1,
  "away_team_id": 2,
  "best_of": 5,
  "points_per_set": 25,
  "tiebreak_points": 15,
  "substitutions_per_set": 6,
  "timeouts_per_set": 2
}
```
Die Regel-Felder sind optional (Defaults wie gezeigt) — damit sind auch
Sonderformate (z. B. Best-of-3 bis 21) möglich. Heim- ≠ Gastteam, sonst 422.

### `GET /api/matches/{match_id}`
Einzelnes Match im selben Format wie die Liste.

### `GET /api/matches/{match_id}/sets`
Sätze eines Matches (Analyse-Strang, `match_sets`), aufsteigend nach `number`:

```json
[{ "number": 1, "home_points": 25, "away_points": 20, "finished": true, "duration_minutes": 24 }]
```

Leere Liste, wenn noch keine Sätze importiert/übernommen wurden (z. B. bei einem
live gescouteten Match vor Roadmap 2.7) — kein Fehler, nur 404 bei unbekannter
`match_id`. Basis für den Match-Browser im Frontend (`MatchDetailView.vue`).

---

## DVW-Import

### `POST /api/imports/dvw` → 201
Multipart-Upload (`file` = `.dvw`-Datei, max. 5 MB). Parst die DataVolley-Datei
(Legacy-Codepage CP1252 wird erkannt), legt fehlende Teams/Spieler an
(vorhandene werden über Team-Code/-Name bzw. Trikotnummer wiederverwendet) und
importiert Match, Sätze, Ballwechsel und Aktionen in den Analyse-Strang:

```json
{ "match_id": 12, "teams_created": 2, "players_created": 24,
  "sets": 3, "rallies": 134, "actions": 445 }
```

Ungültige Datei → 422; Rolle `viewer` → 403.

---

## Statistik-Auswertung

### `GET /api/matches/{match_id}/statistics`
Berechnet die Statistik über alle Sätze/Ballwechsel eines Matches (Analyse-
Strang: `match_sets`/`rallies`/`scout_actions`) — Formeln aus der DV4-Recherche
(siehe `engine/statistics.py`). Match ohne importierte/abgeschlossene Daten
liefert leere Listen/`null`-Quoten, nicht 404 (404 nur bei unbekannter
`match_id`).

```json
{
  "home_players": [
    { "player_number": 7,
      "serve": { "total": 12, "errors": 1, "aces": 2 },
      "reception": { "total": 0, "errors": 0, "positive": 0, "perfect": 0,
                     "positive_pct": null, "perfect_pct": null },
      "attack": { "total": 30, "errors": 3, "blocked": 2, "kills": 14,
                  "efficiency": 0.3, "kill_pct": 46.7 },
      "block": { "total": 30, "points": 4 } }
  ],
  "away_players": [ "…gleiches Schema…" ],
  "home_team": {
    "rallies_served": 40, "points_won_serving": 26,
    "rallies_received": 38, "points_won_receiving": 19,
    "points_total": 45, "break_rate": 65.0, "side_out_rate": 50.0,
    "point_sources": { "serve": 4, "attack": 14, "block": 3, "opponent_errors": 24 }
  },
  "away_team": { "…gleiches Schema…" },
  "home_rotations": [
    { "position": 1, "rallies_served": 8, "points_won_serving": 5,
      "rallies_received": 6, "points_won_receiving": 3,
      "break_rate": 62.5, "side_out_rate": 50.0 }
  ],
  "away_rotations": [ "…gleiches Schema, Position 1–6…" ]
}
```

- **Serve**: `aces`/`errors` = Bewertung `#`/`=`.
- **Reception**: `positive` = Bewertung `+` oder `#` (Annahme-Positivquote),
  `perfect` = nur `#`.
- **Attack**: `efficiency` = (Kills − Errors − Blocked) / Total (klassische
  Angriffseffizienz); `blocked` = Bewertung `/` (Angriff geblockt, Punkt Gegner).
- **Block**: `points` = Bewertung `#` (Blockpunkt).
- **Team**: `break_rate` = Punkte bei eigenem Aufschlag / eigene Aufschlag-
  Ballwechsel; `side_out_rate` = Punkte bei gegnerischem Aufschlag / eigene
  Annahme-Ballwechsel. `point_sources.opponent_errors` ist ein **Residual**
  (Gesamtpunkte − Serve − Angriff − Block), analog zum DV4-Report.
- **Rotation**: dieselben Kennzahlen gruppiert nach der Setterposition (1–6)
  aus dem DVW-Feld `sp_home/guest_setter_pos`, je Team separat für eigenen
  Aufschlag und eigene Annahme.
- Quoten sind `null` (statt `0`), wenn die zugehörige Ballwechsel-Anzahl `0` ist.

## Live-Scouting

Alle Endpunkte liegen unter `/api/matches/{match_id}/live/…` und geben — außer
bei Fehlern — den **kompletten aktuellen Spielzustand** zurück (siehe unten).
Jede Eingabe wird als Event persistiert (Event-Sourcing, siehe
`docs/ARCHITEKTUR.md`); Regelverstöße liefern 422 und verändern nichts.

### Zustandsobjekt (Antwort aller Live-Endpunkte)

```json
{
  "sets_won": { "home": 1, "away": 0 },
  "match_finished": false,
  "set_running": true,
  "set_scores": [ { "number": 1, "home": 25, "away": 21,
    "lineups": { "home": [7,12,4,9,2,15], "away": [8,11,6,1,10,3] } } ],
  "current_set": {
    "number": 2,
    "points": { "home": 3, "away": 4 },
    "serving": "away",
    "lineups": { "home": [7,12,4,9,2,15], "away": [8,11,6,1,10,3] },
    "substitutions": { "home": 1, "away": 0 },
    "timeouts": { "home": 0, "away": 1 },
    "rally_count": 7
  }
}
```

`lineups` ist je Team die Liste `[Zone1, Zone2, …, Zone6]` (Zone 1 = Aufschlag-
position hinten rechts). `current_set` ist `null`, wenn gerade kein Satz läuft.
`set_scores[].lineups` ist die **Endaufstellung** des jeweiligen Satzes (inkl.
während des Satzes gemachter Wechsel) — das Frontend schlägt daraus die
Aufstellung für den nächsten Satz vor (analog zu DataVolley, siehe unten).

### `GET …/live/state`
Nur lesen, z. B. für Anzeige-Clients.

### `POST …/live/set`
Satz starten (nur möglich, wenn kein Satz läuft und das Match nicht beendet ist):
```json
{ "serving": "home", "home_lineup": [7,12,4,9,2,15], "away_lineup": [8,11,6,1,10,3] }
```

### `POST …/live/rally`
Ballwechsel abschließen („End Rally"):
```json
{ "winner": "away", "actions": ["7SQ-", "a3RQ+", "a6AH#"] }
```
`actions` ist optional: Scout-Codes im DataVolley-Main-Code-Format
(`[*|a]<Nummer><Skill S|R|A|B|D|E|F><Typ H|M|Q|T|U|N|O?><Bewertung #|+|!|-|/|=?><Startzone?><Endzone?>`;
ohne Präfix gilt Heimteam). Ungültige Codes → 422, nichts wird gespeichert.
Die Engine übernimmt Punktvergabe, Side-Out, Rotation, Satz- und Matchende.

### `POST …/live/substitution`
```json
{ "side": "home", "player_out": 7, "player_in": 19 }
```

### `POST …/live/timeout`
```json
{ "side": "away" }
```

### `POST …/live/undo`
Letztes Event (Rally, Wechsel, Auszeit oder Satzstart) zurücknehmen; 422, wenn
keine Events vorhanden sind. Der `status` des Matches wird entsprechend
zurückgesetzt (`finished` → `live` → `scheduled`).

---

## Typischer Ablauf (curl)

```bash
B=http://localhost:8080/api
H=$(curl -s -X POST $B/teams -H 'Content-Type: application/json' \
  -d '{"code":"TSV","name":"Heim"}' | jq .id)
A=$(curl -s -X POST $B/teams -H 'Content-Type: application/json' \
  -d '{"code":"VCG","name":"Gast"}' | jq .id)
M=$(curl -s -X POST $B/matches -H 'Content-Type: application/json' \
  -d "{\"match_date\":\"2026-07-27\",\"home_team_id\":$H,\"away_team_id\":$A}" | jq .id)
curl -s -X POST $B/matches/$M/live/set -H 'Content-Type: application/json' \
  -d '{"serving":"home","home_lineup":[1,2,3,4,5,6],"away_lineup":[11,12,13,14,15,16]}'
curl -s -X POST $B/matches/$M/live/rally -H 'Content-Type: application/json' \
  -d '{"winner":"away","actions":["1SQ-","a12RQ+","a14AH#"]}'
```
