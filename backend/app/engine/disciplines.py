"""Disziplin-Voreinstellungen für unterschiedliche Volleyball-Spielformen.

Volleyball wird nicht nur 6:6 in der Halle gespielt — Jugend-Kleinfeldformen
(2:2/3:3/4:4) und Beach-Volleyball (2:2) haben eigene Regelwerke (Feldbesetzung,
Punktziel, Wechsel-/Auszeitlimits). `MatchEngine`/`Rules` (`match_engine.py`)
waren dafür bereits vollständig generisch (jedes Feld war schon parametrisierbar,
inklusive `players_on_court` — nur nie über `Match` befüllt); dieses Modul liefert
lediglich sinnvolle **Startwerte** je Disziplin, die beim Anlegen eines Matches
(`app/api/matches.py::create_match`) nur für nicht explizit gesetzte Felder
greifen — jedes einzelne Feld bleibt weiterhin frei überschreibbar (z. B. ein
Verein, der seine Kinder-Mannschaft abweichend auf 15 statt 25 Punkte spielen
lässt).

**Quellenlage** (siehe `docs/SPIELFORMATE.md` für die vollständige Recherche
mit Quellenangaben): Beach-Volleyball ist über die offiziellen FIVB-Regeln
2025–2028 verifiziert (21 Punkte, Tiebreak 15, keine Wechsel, kein Libero,
1 Auszeit/Satz). Die Jugend-Kleinfeldformen (2:2/3:3/4:4) sind **nicht**
bundeseinheitlich geregelt — jeder Landesverband (NRW, VMV, Hamburg, …) führt
eine eigene Jugendspielordnung mit teils abweichenden Werten; die hier
hinterlegten Presets (Best-of-3, 25/15 Punkte, keine Sonderregeln) sind ein
plausibler Startwert aus den recherchierten Quellen, **kein** verifizierter
bundesweiter Standard. Insbesondere die bei mehreren Landesverbänden übliche
Sonderregel „nach 2 eigenen Punkten in Folge rotieren, Aufschlag behalten"
(Fairness-Regel für Kinder-Volleyball) wird bewusst **nicht** automatisch
durchgesetzt (die Engine rotiert weiterhin nur bei Side-Out) — Scouts können
das bei Bedarf über den bereits bestehenden `correct_lineup`-Event manuell
nachführen (`POST .../live/lineup-correction`).

Ebenfalls bewusst **nicht** Teil dieser Version: eigene Zonen-/Rotations-
Grafiken für Nicht-6:6-Formate (`VolleyballCourt.vue`/`RotationCourt.vue`
bleiben auf das 6-Zonen-Raster ausgelegt) — `has_rotation_zones` steuert im
Frontend nur, ob diese Feld-Helfer überhaupt angezeigt werden
(`LiveScoutView.vue`); für Formate ohne sie bleibt die freie Scout-Code-
Texteingabe der einzige Weg, Zonen zu erfassen.
"""

from dataclasses import dataclass
from enum import Enum


class Discipline(str, Enum):
    HALL_6 = "hall_6"
    HALL_4 = "hall_4"
    HALL_3 = "hall_3"
    HALL_2 = "hall_2"
    BEACH_2 = "beach_2"


@dataclass(frozen=True)
class DisciplinePreset:
    label: str
    players_on_court: int
    best_of: int
    points_per_set: int
    tiebreak_points: int
    substitutions_per_set: int
    timeouts_per_set: int
    has_libero: bool
    # Ob das 6-Zonen-Rotationsraster (RotationCourt.vue/VolleyballCourt.vue)
    # sinnvoll darstellbar ist — nur für die reguläre 6:6-Aufstellung der Fall.
    has_rotation_zones: bool


DISCIPLINE_PRESETS: dict[Discipline, DisciplinePreset] = {
    Discipline.HALL_6: DisciplinePreset(
        label="Halle 6:6",
        players_on_court=6,
        best_of=5,
        points_per_set=25,
        tiebreak_points=15,
        substitutions_per_set=6,
        timeouts_per_set=2,
        has_libero=True,
        has_rotation_zones=True,
    ),
    Discipline.HALL_4: DisciplinePreset(
        label="Halle 4:4 (Jugend, z. B. U14/U16)",
        players_on_court=4,
        best_of=3,
        points_per_set=25,
        tiebreak_points=15,
        substitutions_per_set=6,
        timeouts_per_set=2,
        has_libero=False,
        has_rotation_zones=False,
    ),
    Discipline.HALL_3: DisciplinePreset(
        label="Halle 3:3 (Jugend, z. B. U13)",
        players_on_court=3,
        best_of=3,
        points_per_set=25,
        tiebreak_points=15,
        substitutions_per_set=6,
        timeouts_per_set=2,
        has_libero=False,
        has_rotation_zones=False,
    ),
    Discipline.HALL_2: DisciplinePreset(
        label="Kinder-Volleyball 2:2 (z. B. U12)",
        players_on_court=2,
        best_of=3,
        points_per_set=25,
        tiebreak_points=15,
        substitutions_per_set=6,
        timeouts_per_set=2,
        has_libero=False,
        has_rotation_zones=False,
    ),
    Discipline.BEACH_2: DisciplinePreset(
        label="Beach-Volleyball 2:2",
        players_on_court=2,
        best_of=3,
        points_per_set=21,
        tiebreak_points=15,
        substitutions_per_set=0,
        timeouts_per_set=1,
        has_libero=False,
        has_rotation_zones=False,
    ),
}

DEFAULT_DISCIPLINE = Discipline.HALL_6
