# Spielformate & Zuspielsysteme

Recherche- und Entscheidungsgrundlage für die Mehrfach-Formate-Unterstützung
(`app/engine/disciplines.py`) — Volleyball wird nicht nur 6:6 in der Halle
gespielt, und Teams unterscheiden sich zusätzlich darin, mit wie vielen
Zuspielern sie ihre Rotation aufbauen. Beides betrifft dieses Tool an
unterschiedlichen Stellen: die **Disziplin** bestimmt die Regelparameter eines
Matches (Feldbesetzung, Punktziel, Wechsel-/Auszeitlimits), das
**Zuspielsystem** ist eine reine Team-Eigenschaft ohne Einfluss auf die
Engine-Regeln.

## 1. Disziplinen (`Match.discipline`, `app/engine/disciplines.py`)

| Code | Bezeichnung | Spieler/Feld | Sätze | Punkte/Satz | Tiebreak | Wechsel/Satz | Auszeiten/Satz | Libero |
|---|---|---|---|---|---|---|---|---|
| `hall_6` | Halle 6:6 | 6 | Best-of-5 | 25 | 15 | 6 | 2 | ja |
| `hall_4` | Halle 4:4 (Jugend) | 4 | Best-of-3 | 25 | 15 | 6 | 2 | nein |
| `hall_3` | Halle 3:3 (Jugend) | 3 | Best-of-3 | 25 | 15 | 6 | 2 | nein |
| `hall_2` | Kinder-Volleyball 2:2 | 2 | Best-of-3 | 25 | 15 | 6 | 2 | nein |
| `beach_2` | Beach-Volleyball 2:2 | 2 | Best-of-3 | 21 | 15 | 0 | 1 | nein |

Diese Tabelle sind **Startwerte** für `POST /api/matches` (`MatchCreate.discipline`)
— jedes einzelne Regelfeld (`players_on_court`, `best_of`, `points_per_set`,
`tiebreak_points`, `substitutions_per_set`, `timeouts_per_set`) bleibt beim
Anlegen einzeln überschreibbar (`app/api/matches.py::create_match`: `None` im
Request übernimmt den Preset-Wert, ein gesetzter Wert überschreibt ihn). Die
Werte selbst kommen mit unterschiedlicher Verlässlichkeit:

### Beach-Volleyball 2:2 — FIVB-verifiziert

Quelle: [FIVB Beach Volleyball Rules 2025–2028](https://www.fivb.com/wp-content/uploads/2025/02/FIVB-BeachVolleyball_Rules2025_2028-EN-v01.pdf),
[FIVB Basic Rules](https://www.fivb.com/beach-volleyball/the-game/basic-rules/):

- Sätze bis 21 Punkte (2 Punkte Vorsprung), Best-of-3, Entscheidungssatz bis 15.
- **Keine Auswechslungen** während des Matches — beide Spieler:innen eines
  Teams müssen durchgehend im Spiel sein (`substitutions_per_set = 0`).
- Kein Libero (folgt zwingend aus der fehlenden Wechselmöglichkeit).
- 1 Auszeit (30 s) pro Satz; zusätzlich ein automatisches technisches
  Timeout in Satz 1/2 bei Kombi-Punktstand 21 — **nicht** in der Engine
  automatisiert (Scouts setzen die reguläre Auszeit-Aktion bei Bedarf manuell).

### Jugend-Kleinfeldformen (2:2/3:3/4:4) — **nicht** bundeseinheitlich verifiziert

Anders als beim Beach-Volleyball gibt es in Deutschland **keine einzige**
DVV-Jugendspielordnung — jeder Landesverband (NRW, VMV, Hamburg, …) führt eine
eigene, teils abweichende Fassung. Recherchierte Eckpunkte (Quellen: Auszüge
aus Landesverbands-Jugendspielordnungen, u. a. Volleyball-Verband NRW,
Volleyball-Verband Mecklenburg-Vorpommern):

- Rally-Point-Zählweise gilt durchgehend.
- Generell zwei Gewinnsätze (Best-of-3), Entscheidungssatz bis 15 Punkte,
  Seitenwechsel bei 8 Punkten im Entscheidungssatz.
- Feldgrößen variieren nach Altersklasse (z. B. U12 2:2 auf 9,00 m × 4,50 m,
  zwei Hälften à 4,50 m × 4,50 m; U13 3:3 auf 12,00 m × 6,00 m; U16 4:4 auf
  7 m × 7 m) — für dieses Tool ohne Relevanz, da es keine
  formatspezifische Court-Grafik zeichnet (siehe Abschnitt 3).
- Verbreitete Sonderregel bei mehreren Landesverbänden (U12–U14): **erzielt
  eine Mannschaft zwei Punkte in Folge im eigenen Aufschlag, rotiert sie
  einmal, behält aber den Aufschlag** — eine Fairness-Regel, damit alle
  Kinder zum Aufschlag kommen. Diese Regel ist **bewusst nicht in der Engine
  automatisiert** (siehe Abschnitt 4).

Die 25/15-Punktewerte in der Presets-Tabelle sind aus diesen Quellen
plausibel abgeleitet, aber **kein verifizierter bundesweiter Standard** —
Vereine mit abweichender Landesverbandsregel überschreiben `points_per_set`
u. Ä. beim Match-Anlegen einfach individuell.

## 2. Zuspielsysteme (`Team.setter_system`, `app/schemas/team.py::SetterSystem`)

Recherchequellen: [volleyballxl.de – Volleyballsysteme erklärt](https://volleyballxl.de/volleyballsysteme/),
[Volleyball-Insider – 5-1-Läufersystem](https://volleyball-insider.com/training/taktik/laefer-system-5-1-volleyball/),
[Goldmedal Squared – 6-6 Offense](https://www.goldmedalsquared.com/post/6-6-offensive-system).

| Code | Zuspieler | Zuspiel aus | Angreifer | Typisches Niveau |
|---|---|---|---|---|
| `5-1` | 1 (spielt alle 6 Rotationen) | vorne + hinten | 5 | Standard im Leistungssport |
| `6-2` | 2 (immer gegenüberliegend) | nur hinten (vorne wird zum 3. Angreifer) | 6 potenziell | Teams mit zwei starken Zuspielern |
| `4-2` | 2 (immer gegenüberliegend) | nur vorne | 4 | Jugend/Einsteiger — einfachste Variante |
| `6-6` | keiner fest | wer gerade an der Ballstelle steht | alle | Kinder-/Mini-Volleyball, absolute Anfänger |

**Wichtig: dieses Feld beeinflusst keine einzige Engine-Regel** — es ist reine
Dokumentation/Anzeige im Kader (`TeamsView.vue`). Der Grund: die bereits
bestehende `Player.is_primary_setter`-Kennzeichnung plus ihr Fallback auf die
Position „Zuspieler" (`app/engine/rotation.py::setter_zone`, siehe
`docs/ARCHITEKTUR.md`) bildet alle vier Systeme bereits korrekt ab, ohne dass
die Engine wissen muss, welches System ein Team spielt:

- **5-1**: nur ein Zuspieler im Kader → automatisch eindeutig, `is_primary_setter`
  wird nicht einmal gebraucht.
- **6-2**: zwei Zuspieler, aber durch die Rotation nie beide gleichzeitig auf
  dem Feld in setzender Position (der vordere wird zum Angreifer) →
  `setter_zone()`s Fallback auf „wer steht gerade als Zuspieler auf dem
  Feld" liefert bereits die richtige Zone.
- **4-2**: beide Zuspieler **können** gleichzeitig auf dem Feld stehen (kein
  Rotations-Zwang wie bei 6-2) — genau für diesen Fall existiert
  `is_primary_setter` als Tie-Breaker: der Kaderpfleger markiert den
  Referenz-Zuspieler, dessen Zone den angezeigten Rotationscode bestimmt.
- **6-6**: kein Spieler mit Position „Zuspieler" oder `is_primary_setter`
  gesetzt → `setter_zone()` liefert `None`, die Anzeige zeigt „–" statt eine
  erfundene Zone. Korrektes Verhalten, kein Sonderfall nötig.

## 3. Bewusst nicht Teil dieser Version

- **Keine formatspezifische Court-/Zonengrafik.** `VolleyballCourt.vue`
  (9-Zonen-Raster) und `RotationCourt.vue` (6-Zonen-Rotationsraster) bleiben
  auf die reguläre 6:6-Hallenaufstellung ausgelegt (siehe
  `DisciplinePreset.has_rotation_zones`). Für alle anderen Disziplinen zeigt
  `LiveScoutView.vue` nur eine schlichte Positionsliste (kein Feld-Helfer);
  Zonen lassen sich bei Bedarf weiterhin über die freie Scout-Code-
  Texteingabe erfassen (z. B. `14AH+45`, siehe `docs/ARCHITEKTUR.md`).
- **Die „2 Punkte in Folge → rotieren, Aufschlag behalten"-Sonderregel**
  einzelner Jugend-Landesverbände wird **nicht automatisch** durchgesetzt —
  die Engine rotiert weiterhin ausschließlich bei Side-Out (Standard-
  Rally-Point-Regel, die für alle fünf Disziplinen tatsächlich identisch
  gilt). Scouts, deren Verband diese Sonderregel nutzt, können die Rotation
  manuell über den bereits bestehenden `correct_lineup`-Event nachführen
  (`POST .../live/lineup-correction`, gedacht für genau solche
  Erfassungskorrekturen, siehe `docs/ARCHITEKTUR.md`).
- **Kein automatisches technisches Timeout** (Beach, Kombi-Punktstand 21).
- **Keine Libero-Sonderregeln** in der Engine (Wechsel zählt für alle
  Disziplinen gleich gegen das reguläre Wechsellimit) — offener Punkt
  unabhängig von den Formaten, siehe `docs/ARCHITEKTUR.md` Roadmap-Notizen.

## 4. Warum die Engine dafür kaum geändert werden musste

`MatchEngine`/`Rules` (`app/engine/match_engine.py`) waren von Anfang an
vollständig generisch parametrisiert — `players_on_court` war schon immer ein
Feld auf `Rules`, nur nie über `Match` befüllt (Default blieb 6). Rotation
(`lineup[1:] + lineup[:1]`), Aufstellungs-/Wechsel-Validierung (`len(lineup)
== rules.players_on_court`) und Satzende-Logik funktionieren für jede
Listenlänge identisch. Diese Version ergänzt also nur:

1. `Match.discipline`/`Match.players_on_court` als neue Spalten (Migration
   `0008`) plus die drei Stellen, die `Rules(...)` bauen
   (`app/api/live.py`, `app/analyse_sync.py`, `app/dvw/exporter.py`), um
   `players_on_court` durchzureichen.
2. Die Presets/Enums selbst (`app/engine/disciplines.py`,
   `SetterSystem` in `app/schemas/team.py`).
3. Frontend-Anpassungen, die die feste 6er-Annahme an zwei Stellen auflösen
   (`LiveScoutView.vue`: Aufstellungs-Slots + bedingtes Ausblenden der
   Feld-Helfer).

Kein einziger bestehender Test musste inhaltlich geändert werden (`hall_6`
bleibt exakt das bisherige Verhalten) — `tests/test_disciplines.py` deckt die
neuen Pfade ab (Preset-Auflösung, Override einzelner Felder, ein komplettes
2-Spieler-Match inkl. abgelehntem Wechsel, Export).
