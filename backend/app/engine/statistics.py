"""Statistik-Auswertung für den Analyse-Strang (importierte/abgeschlossene Matches).

Reine Berechnungslogik ohne DB-Abhängigkeit — operiert auf bereits geladenen
Rally-/Aktionsdaten (`RallyRow`/`ActionRow`), analog zum Aufbau von
`match_engine.py`. Formeln nach der DV4-Funktionsanalyse (Report-Statistiken,
Abschnitt 5 der Recherche):

- Serve: Tot/Err(`=`)/Ass(`#`)
- Reception: Tot/Err(`=`)/Pos% (`+`+`#`)/Exc% (`#`)
- Attack: Tot/Err(`=`)/Blocked(`/`)/Kills(`#`), Effizienz = (Kills−Err−Blocked)/Tot
- Block: Tot/Punkte(`#`)
- Team: Side-Out-Quote (Punkte bei Annahme/Ballwechsel bei Annahme), Break-Quote
  (Punkte bei eigenem Aufschlag/Ballwechsel bei eigenem Aufschlag), Punktquellen
  mit „Opponent Errors" als **Residual** (Gesamtpunkte − Serve − Angriff − Block),
  exakt wie im DV4-Report definiert.
- Rotation: dieselben Kennzahlen gruppiert nach der Setterposition (1–6) aus dem
  DVW-Feld `sp_home_setter_pos`/`sp_guest_setter_pos` (siehe `docs/DVW-FORMAT.md`
  Abschnitt 2.12) — pro Rally auf `Rally.home_setter_position`/`away_setter_position`
  übernommen.
"""

from dataclasses import dataclass, field
from typing import Literal

Side = Literal["home", "away"]
SIDES: tuple[Side, Side] = ("home", "away")

_POINT_SKILLS = {"S", "A", "B"}  # Skills, deren Bewertung `#` einen direkten Punkt bedeutet


@dataclass
class ActionRow:
    side: Side
    player_number: int | None
    skill: str | None  # S R A B D E F
    evaluation: str | None  # # + ! - / =


@dataclass
class RallyRow:
    serving_side: Side
    winner_side: Side
    home_setter_position: int | None
    away_setter_position: int | None
    actions: list[ActionRow] = field(default_factory=list)


@dataclass
class PlayerServeStats:
    player_number: int
    total: int = 0
    errors: int = 0
    aces: int = 0


@dataclass
class PlayerReceptionStats:
    player_number: int
    total: int = 0
    errors: int = 0
    positive: int = 0  # Bewertung `+` oder `#`
    perfect: int = 0  # Bewertung `#`

    @property
    def positive_pct(self) -> float | None:
        return (self.positive / self.total * 100) if self.total else None

    @property
    def perfect_pct(self) -> float | None:
        return (self.perfect / self.total * 100) if self.total else None


@dataclass
class PlayerAttackStats:
    player_number: int
    total: int = 0
    errors: int = 0
    blocked: int = 0
    kills: int = 0

    @property
    def efficiency(self) -> float | None:
        return ((self.kills - self.errors - self.blocked) / self.total) if self.total else None

    @property
    def kill_pct(self) -> float | None:
        return (self.kills / self.total * 100) if self.total else None


@dataclass
class PlayerBlockStats:
    player_number: int
    total: int = 0
    points: int = 0


@dataclass
class PlayerStatistics:
    side: Side
    player_number: int
    serve: PlayerServeStats
    reception: PlayerReceptionStats
    attack: PlayerAttackStats
    block: PlayerBlockStats


@dataclass
class PointSources:
    serve: int = 0
    attack: int = 0
    block: int = 0
    opponent_errors: int = 0


@dataclass
class TeamStatistics:
    side: Side
    rallies_served: int = 0
    points_won_serving: int = 0
    rallies_received: int = 0
    points_won_receiving: int = 0
    point_sources: PointSources = field(default_factory=PointSources)

    @property
    def points_total(self) -> int:
        return self.points_won_serving + self.points_won_receiving

    @property
    def break_rate(self) -> float | None:
        return (self.points_won_serving / self.rallies_served * 100) if self.rallies_served else None

    @property
    def side_out_rate(self) -> float | None:
        return (
            (self.points_won_receiving / self.rallies_received * 100)
            if self.rallies_received
            else None
        )


@dataclass
class RotationStats:
    position: int
    rallies_served: int = 0
    points_won_serving: int = 0
    rallies_received: int = 0
    points_won_receiving: int = 0

    @property
    def break_rate(self) -> float | None:
        return (self.points_won_serving / self.rallies_served * 100) if self.rallies_served else None

    @property
    def side_out_rate(self) -> float | None:
        return (
            (self.points_won_receiving / self.rallies_received * 100)
            if self.rallies_received
            else None
        )


@dataclass
class MatchStatistics:
    players: dict[Side, list[PlayerStatistics]]
    teams: dict[Side, TeamStatistics]
    rotations: dict[Side, list[RotationStats]]


def compute_match_statistics(rallies: list[RallyRow]) -> MatchStatistics:
    serve: dict[Side, dict[int, PlayerServeStats]] = {side: {} for side in SIDES}
    reception: dict[Side, dict[int, PlayerReceptionStats]] = {side: {} for side in SIDES}
    attack: dict[Side, dict[int, PlayerAttackStats]] = {side: {} for side in SIDES}
    block: dict[Side, dict[int, PlayerBlockStats]] = {side: {} for side in SIDES}
    teams: dict[Side, TeamStatistics] = {side: TeamStatistics(side=side) for side in SIDES}
    rotations: dict[Side, dict[int, RotationStats]] = {side: {} for side in SIDES}

    for rally in rallies:
        for side in SIDES:
            team = teams[side]
            if rally.serving_side == side:
                team.rallies_served += 1
                if rally.winner_side == side:
                    team.points_won_serving += 1
            else:
                team.rallies_received += 1
                if rally.winner_side == side:
                    team.points_won_receiving += 1

            position = (
                rally.home_setter_position if side == "home" else rally.away_setter_position
            )
            if position is not None:
                rotation = rotations[side].setdefault(position, RotationStats(position=position))
                if rally.serving_side == side:
                    rotation.rallies_served += 1
                    if rally.winner_side == side:
                        rotation.points_won_serving += 1
                else:
                    rotation.rallies_received += 1
                    if rally.winner_side == side:
                        rotation.points_won_receiving += 1

        for action in rally.actions:
            if action.player_number is None or action.skill is None:
                continue
            num = action.player_number
            side_stats = action.side
            if action.skill == "S":
                stats = serve[side_stats].setdefault(num, PlayerServeStats(player_number=num))
                stats.total += 1
                if action.evaluation == "=":
                    stats.errors += 1
                elif action.evaluation == "#":
                    stats.aces += 1
            elif action.skill == "R":
                rec = reception[side_stats].setdefault(
                    num, PlayerReceptionStats(player_number=num)
                )
                rec.total += 1
                if action.evaluation == "=":
                    rec.errors += 1
                if action.evaluation in ("+", "#"):
                    rec.positive += 1
                if action.evaluation == "#":
                    rec.perfect += 1
            elif action.skill == "A":
                atk = attack[side_stats].setdefault(num, PlayerAttackStats(player_number=num))
                atk.total += 1
                if action.evaluation == "=":
                    atk.errors += 1
                elif action.evaluation == "/":
                    atk.blocked += 1
                elif action.evaluation == "#":
                    atk.kills += 1
            elif action.skill == "B":
                blk = block[side_stats].setdefault(num, PlayerBlockStats(player_number=num))
                blk.total += 1
                if action.evaluation == "#":
                    blk.points += 1

        # Punktquelle: die den Ballwechsel beendende Aktion ist immer die letzte in der
        # Liste (Importer schließt die Rally genau an dieser Stelle ab).
        if rally.actions:
            closing = rally.actions[-1]
            if (
                closing.side == rally.winner_side
                and closing.evaluation == "#"
                and closing.skill in _POINT_SKILLS
            ):
                sources = teams[rally.winner_side].point_sources
                if closing.skill == "S":
                    sources.serve += 1
                elif closing.skill == "A":
                    sources.attack += 1
                elif closing.skill == "B":
                    sources.block += 1

    for side in SIDES:
        sources = teams[side].point_sources
        sources.opponent_errors = teams[side].points_total - (
            sources.serve + sources.attack + sources.block
        )

    players: dict[Side, list[PlayerStatistics]] = {side: [] for side in SIDES}
    for side in SIDES:
        numbers = set(serve[side]) | set(reception[side]) | set(attack[side]) | set(block[side])
        for num in sorted(numbers):
            players[side].append(
                PlayerStatistics(
                    side=side,
                    player_number=num,
                    serve=serve[side].get(num, PlayerServeStats(player_number=num)),
                    reception=reception[side].get(num, PlayerReceptionStats(player_number=num)),
                    attack=attack[side].get(num, PlayerAttackStats(player_number=num)),
                    block=block[side].get(num, PlayerBlockStats(player_number=num)),
                )
            )

    rotation_lists: dict[Side, list[RotationStats]] = {
        side: sorted(rotations[side].values(), key=lambda r: r.position) for side in SIDES
    }

    return MatchStatistics(players=players, teams=teams, rotations=rotation_lists)
