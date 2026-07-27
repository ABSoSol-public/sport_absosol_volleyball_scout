# Datenbank

Stand: 2026-07-28. Einzige Datenbank ist die **MariaDB 10.11 auf der Synology**
(`SYNOLOGY_DB_*` in der `.env`) — sowohl für die lokale Entwicklung als auch im
NAS-Deployment; einen lokalen DB-Container gibt es bewusst nicht
(Nutzerentscheidung 2026-07-28). Charset utf8mb4. Die Tests laufen gegen
SQLite in-memory. ORM-Definitionen: `backend/app/models/entities.py`.

## Migrationen (Alembic)

- Konfiguration: `backend/alembic.ini` + `backend/alembic/env.py` (zieht die
  DB-URL aus der App-Konfiguration, keine URL im Ini-File).
- Initial-Schema: `backend/alembic/versions/0001_initial.py`.
- Im Container laufen Migrationen **automatisch** beim Start
  (`docker-entrypoint.sh`: auf DB warten → `alembic upgrade head` → uvicorn).
- Neue Migration anlegen: `cd backend && .venv/bin/alembic revision -m "…"`
  (bei Autogenerate gegen eine laufende MariaDB; generierte Datei reviewen).

## Schema-Überblick

```
teams ──< players
teams ──< matches (home_team_id / away_team_id)
matches ──< live_events          ← Quelle der Wahrheit fürs Live-Scouting
matches ──< match_sets ──< rallies ──< scout_actions   ← Analyse-/Import-Strang
```

Wichtig: Der Live-Strang schreibt in Version 1.0 **nur `live_events`**.
`match_sets`/`rallies`/`scout_actions` sind für den Analyse-/Import-Strang
(Roadmap 1.1/1.2) angelegt und werden dort befüllt (DVW-Import bzw. Ableitung
aus dem Event-Log).

## Tabellen

### `teams`
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| code | VARCHAR(8) | UNIQUE — Kurzcode (DV4-Vorbild: 3 Buchstaben) |
| name | VARCHAR(120) | |

### `players`
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| team_id | INT FK→teams.id | ON DELETE CASCADE |
| number | INT | UNIQUE je Team (`uq_player_team_number`) |
| last_name / first_name | VARCHAR(80) | |
| position | VARCHAR(20) | Freitext (Setter, Outside, …) |
| is_libero | BOOL | |

### `matches`
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| match_date | DATE | |
| competition | VARCHAR(120) | |
| home_team_id / away_team_id | INT FK→teams.id | |
| best_of | INT | Default 5 |
| points_per_set | INT | Default 25 |
| tiebreak_points | INT | Default 15 |
| substitutions_per_set | INT | Default 6 |
| timeouts_per_set | INT | Default 2 |
| status | VARCHAR(16) | `scheduled` → `live` → `finished` (von der API gepflegt) |
| created_at | DATETIME | UTC |

Die Regel-Spalten machen jedes Match eigenständig reproduzierbar — die Engine
wird pro Match aus genau diesen Werten parametrisiert.

### `live_events` — Quelle der Wahrheit (Event-Sourcing)
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| match_id | INT FK→matches.id | ON DELETE CASCADE |
| seq | INT | fortlaufend je Match, UNIQUE (`uq_event_match_seq`) |
| event_type | VARCHAR(20) | `start_set` \| `rally` \| `substitution` \| `timeout` |
| payload | JSON | siehe unten |
| created_at | DATETIME | UTC — implizite Zeitstempel-Basis für Roadmap 1.6 |

Payload-Formate:

```jsonc
// start_set
{ "serving": "home", "home_lineup": [7,12,4,9,2,15], "away_lineup": [8,11,6,1,10,3] }

// rally — actions sind bereits geparste Scout-Codes (Rohcode bleibt erhalten)
{ "winner": "away", "actions": [
    { "raw_code": "a6AH#", "side": "away", "player_number": 6, "skill": "A",
      "hit_type": "H", "evaluation": "#", "start_zone": null, "end_zone": null } ] }

// substitution
{ "side": "home", "player_out": 7, "player_in": 19 }

// timeout
{ "side": "away" }
```

Undo = Löschen der Zeile mit der höchsten `seq` des Matches. Der Spielzustand
wird nie gespeichert, sondern bei jedem Zugriff per Replay rekonstruiert
(deterministisch, siehe `docs/ARCHITEKTUR.md`).

### `match_sets` (Analyse-Strang, ab Roadmap 1.1/1.2 befüllt)
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| match_id | INT FK→matches.id | CASCADE; UNIQUE (match_id, number) |
| number | INT | Satznummer 1–5 |
| home_points / away_points | INT | Endstand des Satzes |
| finished | BOOL | |
| duration_minutes | INT NULL | wie im DVW-Format (`[3SET]`) |

### `rallies`
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| set_id | INT FK→match_sets.id | CASCADE |
| number | INT | fortlaufend im Satz |
| serving_side / winner_side | VARCHAR(4) | `home` \| `away` |
| home_score_after / away_score_after | INT | Spielstand nach dem Ballwechsel |

### `scout_actions`
| Spalte | Typ | Hinweise |
|---|---|---|
| id | INT PK | |
| rally_id | INT FK→rallies.id | CASCADE |
| seq | INT | Reihenfolge im Ballwechsel |
| raw_code | VARCHAR(40) | Original-Eingabe (verlustfrei) |
| side | VARCHAR(4) | `home` \| `away` |
| player_number | INT NULL | |
| skill | CHAR(1) NULL | S R A B D E F |
| hit_type | CHAR(1) NULL | H M Q T U N O |
| evaluation | CHAR(1) NULL | # + ! - / = |
| start_zone / end_zone | INT NULL | 1–9 |

Die Spalten spiegeln den DataVolley-**Main-Code**; für Advanced/Extended-Anteile
(Kombinationen, Setter-Calls, Subzonen) werden bei Bedarf Spalten ergänzt —
bis dahin bleibt alles verlustfrei im `raw_code`.

## Betrieb

- **Zugriff**: `mysql -h <SYNOLOGY_DB_HOST> -P 3307 -u volleyball_database -p volleyball`
  (Werte aus der git-ignorierten `.env`).
- Das Schema wurde per `alembic upgrade head` eingespielt (2026-07-27,
  MariaDB 10.11); künftige Migrationen laufen beim Backend-Start automatisch.
- **Achtung**: lokale Entwicklung und Deployment schreiben in **dieselbe**
  Datenbank — bis zum Livegang unkritisch, danach für lokale Experimente ggf.
  eine separate DB (z. B. `volleyball_dev`) auf der Synology anlegen und in der
  `.env` umschalten.
- Passwort-Sonderzeichen in der SQLAlchemy-URL URL-encodieren.
- Backup-Strategie: offen (Roadmap 1.8, sinnvoll ab erstem echten Datenbestand).
