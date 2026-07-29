"""Response-Schemas für die Statistik-Auswertung (`GET /matches/{id}/statistics`).

`from_attributes=True` erlaubt die direkte Validierung aus den `engine/statistics.py`-
Dataclasses (inkl. deren berechneten `@property`-Feldern), ohne manuelles Mapping.
"""

from pydantic import BaseModel, ConfigDict


class ServeStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    errors: int
    aces: int


class ReceptionStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    errors: int
    positive: int
    perfect: int
    positive_pct: float | None
    perfect_pct: float | None


class AttackStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    errors: int
    blocked: int
    kills: int
    efficiency: float | None
    kill_pct: float | None


class BlockStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    points: int


class PlayerStatisticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_number: int
    serve: ServeStatsRead
    reception: ReceptionStatsRead
    attack: AttackStatsRead
    block: BlockStatsRead


class PointSourcesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serve: int
    attack: int
    block: int
    opponent_errors: int


class TeamStatisticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rallies_served: int
    points_won_serving: int
    rallies_received: int
    points_won_receiving: int
    points_total: int
    break_rate: float | None
    side_out_rate: float | None
    point_sources: PointSourcesRead


class RotationStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    rallies_served: int
    points_won_serving: int
    rallies_received: int
    points_won_receiving: int
    break_rate: float | None
    side_out_rate: float | None


class MatchStatisticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    home_players: list[PlayerStatisticsRead]
    away_players: list[PlayerStatisticsRead]
    home_team: TeamStatisticsRead
    away_team: TeamStatisticsRead
    home_rotations: list[RotationStatsRead]
    away_rotations: list[RotationStatsRead]
