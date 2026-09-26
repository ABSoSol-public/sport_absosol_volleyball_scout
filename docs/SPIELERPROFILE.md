# Spielerprofile: Karrierestatistik, Skill-Karte & Tendenzen

Nutzerwunsch (wörtlich): „das scouting tool soll auch nach dem vorbild von
NFL ein spielerbasierendes playbook erstellen können (profiling von spielern
über mehrere saisons) und wie bei fifa eine spieler fähigkeiten kachel
erstellen ... mit bewertung über die komplette datenbank als referenz über
alle spieler hinweg ... das muss dynamisch berechnet werden und mit daten
natürlich angereichert werden ... die datenbank soll entsprechend dem
kontext vollumfänglich verbessert und erweitert werden." Dieses Dokument
beschreibt, wie das umgesetzt ist und warum an mehreren Stellen bewusst
**keine** erfundenen Zahlen ins Spiel kommen. Die „Datenbank vollumfänglich
erweitern"-Vorgabe führte zusätzlich zum neuen `Season`-Modell (siehe unten)
— die einzige rein strukturelle Schemaerweiterung dieser Anfrage.

## Spieleridentität ohne eigene Tabelle

`scout_actions` trägt keine `player_id`-Fremdschlüssel, nur `side`
(`home`/`away`) + `player_number` (siehe `docs/DATENBANK.md`). Ein
physischer Spieler wird deshalb — wie schon beim DVW-Export/-Import
(`docs/ARCHITEKTUR.md`) — über das Paar `(team_id, Trikotnummer)`
identifiziert: welches Team an einem gegebenen Match „home"/„away" war, steht
in `Match.home_team_id`/`away_team_id`. Das setzt voraus, dass eine
Trikotnummer innerhalb eines Teams über die Zeit hinweg demselben Menschen
gehört — in der Praxis nahezu immer der Fall, und exakt dieselbe Annahme, die
der Reexport (`app/dvw/exporter.py`) bereits macht.

## Architektur (neue Module)

| Modul | Aufgabe |
|---|---|
| `app/engine/player_profile.py` | DB-freie Aggregation: `aggregate_career_stats()` fasst beliebig viele Aktionen eines Spielers zu Serve-/Reception-/Attack-/Block-Kennzahlen zusammen (nutzt dieselben Formeln wie `app/engine/statistics.py`, dort als `add_serve_action` u. Ä. öffentlich gemacht statt dupliziert); `attack_zone_tendencies()`/`serve_zone_tendencies()` gruppieren nach Zonenkombination. |
| `app/player_data.py` | Lädt `scout_actions` eines Spielers über **alle** Matches (+ optional Disziplin-/Saisonfilter) aus der DB, join über `rallies`→`match_sets`→`matches`. |
| `app/player_card.py` | Skill-Karte: lädt die Aktionen **aller** Spieler derselben Disziplin(+Saison), berechnet je Kategorie einen Perzentilrang (siehe unten). |
| `app/seasons.py` | Saison-Zuordnung (1. Jul.–30. Jun., `get_or_create_season()`), automatisch beim Match-Anlegen (`app/api/matches.py`) und -Import (`app/dvw/importer.py`) aufgerufen. |
| `app/api/players.py` | `GET /api/players/{team_id}/{number}/profile` + `.../card`. |
| `app/api/seasons.py` | `GET /api/seasons` (rein lesend, für Filter-Dropdowns im Frontend). |

## Saisons (`Season`, Migration `0009`)

Eine Saison läuft **1. Juli – 30. Juni** — pragmatischer Schnitt, der sowohl
Hallensaisons (Herbst–Frühjahr, über den Jahreswechsel) als auch
Beach-Saisons (Frühjahr–Herbst) sauber in aufeinanderfolgende Saisonlabel
trennt, statt sie zu vermischen. Wird **automatisch** beim Anlegen
(`POST /api/matches`) bzw. DVW-Import aus `match_date` ermittelt/erzeugt —
kein eigener Verwaltungs-Endpunkt zum manuellen Anlegen. Die Migration
backfillt bestehende Matches rückwirkend anhand ihres `match_date`, damit
auch vor dieser Version gescoutete/importierte Spiele in die
Saisonaufschlüsselung einfließen.

## Karriereprofil (`GET /api/players/{team_id}/{number}/profile`)

Query-Parameter: `discipline` (Default `hall_6`, siehe
`docs/SPIELFORMATE.md`), `season_id` (optional — weggelassen liefert die
gesamte Karriere in dieser Disziplin).

Antwort enthält:
- **`career`**: Serve/Reception/Attack/Block-Kennzahlen (dieselben Formeln
  wie die Einzel-Match-Statistik, siehe `docs/ARCHITEKTUR.md`) über alle
  passenden Matches summiert, plus `matches`/`actions`.
- **`by_season`**: dieselben Kennzahlen, aufgeschlüsselt je Saison
  (absteigend sortiert), für den "Verlauf über mehrere Saisons".
- **`attack_tendencies`**/**`serve_tendencies`**: das NFL-Playbook-Äquivalent
  — Angriffs-/Aufschlag-Zonenkombinationen (`start_zone`→`end_zone`), nach
  Häufigkeit sortiert, mit Erfolgsquote je Kombination. Datenquelle sind die
  ohnehin vorhandenen `scout_actions`-Zonenfelder (aus DVW-Import oder dem
  Zonen-Helfer/Klickpfad bei der Live-Eingabe) — **keine** neue Datenerhebung
  nötig. Kombinationen ohne jede Zonenangabe (häufig bei der kompakten
  Live-Direkteingabe ohne Zonen-Helfer) tauchen als `start_zone`/`end_zone:
  null` auf, nicht versteckt.

## Skill-Karte (`GET /api/players/{team_id}/{number}/card`)

Vier Kategorien (Aufschlag/Annahme/Angriff/Block), je eine Rohkennzahl:

| Kategorie | Metrik |
|---|---|
| Aufschlag | (Asse − Fehler) / Aufschläge |
| Annahme | Positivquote (`+`/`#`) in % |
| Angriff | Effizienz (Kills − Fehler − geblockt) / Angriffe — dieselbe Formel wie in der Match-Statistik |
| Block | Blockpunkte / Blockaktionen |

**Bewertung = Perzentilrang** dieser Rohkennzahl innerhalb der Population
*aller* Spieler derselben Disziplin (+ optional derselben Saison) mit
mindestens `MIN_SAMPLE`-Aktionen in diesem Skill (`app/player_card.py`:
6 für Aufschlag/Annahme/Angriff, 3 für Block — ein bewusst konservativer,
nicht statistisch hergeleiteter Startwert gegen Zufallsausreißer bei sehr
wenigen Versuchen). Die Zielspielerin/der Zielspieler zählt selbst zur
Population dazu ("wo stehst du im Vergleich zu allen, dich eingeschlossen").
Ein Perzentilrang braucht keine Normalverteilungsannahme und bleibt robust
bei den hier realistischen kleinen Vereins-Datenmengen (im Gegensatz zu z. B.
einem z-Score).

**`overall`** ist der Mittelwert der Kategorien mit ausreichender Stichprobe.
Eine Kategorie ohne genug Daten fließt **nicht** als 0 ein — ein Spieler ohne
gescoutete Blockaktionen wäre sonst fälschlich "schlecht im Block" statt
schlicht ungetestet. Jede Kategorie liefert zusätzlich `sample_size` (eigene
Aktionszahl) und `population_size` (wie viele andere Spieler zum Vergleich
herangezogen wurden) — das Frontend zeigt eine Kategorie ohne Rating als „–"
statt einer erfundenen Zahl.

**Vergleichsgruppe ist bewusst auf dieselbe Disziplin beschränkt** — ein
Beach-Aufschlag (21-Punkte-Sätze, 2 Feldspieler) ist nicht mit einem
Hallen-Aufschlag vergleichbar, siehe `docs/SPIELFORMATE.md`. Die Karte nimmt
deshalb immer einen `discipline`-Filter entgegen, nie „alle Formate
gemischt" — ein Spieler, der sowohl Halle als auch Beach spielt, bekommt
zwei getrennte Karten (Disziplin-Auswahl im Frontend).

## Frontend (`PlayerProfileView.vue`, Route `/players/:teamId/:number`)

Erreichbar über einen neuen „Profil"-Button je Kaderzeile in `TeamsView.vue`.
Zeigt Disziplin-/Saison-Filter (aus `GET /api/disciplines`/`GET /api/seasons`),
die Skill-Karte (Gesamt-Zahl + Balken je Kategorie, wiederverwendet die
bestehende `.meter`-Balkenoptik aus dem Match-Browser statt einer neuen
Chart-Bibliothek), zwei Tendenz-Tabellen (Angriff/Aufschlag) und eine
Saisonverlaufs-Tabelle (Gesamt-Zeile + eine Zeile je Saison).

## Bewusst nicht Teil dieser Version

- **Keine DV4-„Noten"** (0–10-Gesamtwertung mit Mindestbeteiligungsquoten,
  siehe `docs/ARCHITEKTUR.md`) — die Skill-Karte ist eine eigenständige,
  datenbankweite Perzentil-Bewertung, kein Versuch, die DV4-Notenformel
  nachzubauen.
- **Kein Spieler-Ranking/Leaderboard** über alle Spieler hinweg (z. B. „Top 10
  Aufschläger der Liga") — nur die Einzelprofil-Ansicht. Ließe sich auf
  derselben Datengrundlage (`app/player_card.py::_load_all_player_actions`)
  ergänzen, war aber nicht Teil dieser Anfrage.
- **Keine Setter-/Rotationstendenzen** (z. B. „gegen welche Rotation greift
  Spieler X am liebsten an") — die Zonentendenzen sind rein aktionsbasiert,
  ohne Verknüpfung zur damaligen Rotation/Setterposition der Gegenseite.
