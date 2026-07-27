# API-Referenz

Stand: Version 1.0 (2026-07-27). Basis-URL: `/api` (im Compose-Stack über das
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
      "position": "Setter", "is_libero": false }
  ]
}
```

### `POST /api/teams/{team_id}/players` → 201
```json
{ "number": 7, "last_name": "Musterfrau", "first_name": "Erika",
  "position": "Setter", "is_libero": false }
```
`number` 0–99, pro Team eindeutig → 409 bei Doppelvergabe.

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
  "set_scores": [ { "number": 1, "home": 25, "away": 21 } ],
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
