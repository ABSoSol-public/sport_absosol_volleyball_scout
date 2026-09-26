from pydantic import BaseModel

from app.schemas.season import SeasonRead


class ServeStatsRead(BaseModel):
    total: int
    errors: int
    aces: int


class ReceptionStatsRead(BaseModel):
    total: int
    errors: int
    positive: int
    perfect: int
    positive_pct: float | None
    perfect_pct: float | None


class AttackStatsRead(BaseModel):
    total: int
    errors: int
    blocked: int
    kills: int
    efficiency: float | None
    kill_pct: float | None


class BlockStatsRead(BaseModel):
    total: int
    points: int


class CareerStatsRead(BaseModel):
    serve: ServeStatsRead
    reception: ReceptionStatsRead
    attack: AttackStatsRead
    block: BlockStatsRead
    matches: int
    actions: int


class SeasonBreakdownRead(BaseModel):
    season: SeasonRead
    stats: CareerStatsRead


class ZoneTendencyRead(BaseModel):
    start_zone: int | None
    end_zone: int | None
    attempts: int
    positive: int
    errors: int
    blocked: int
    positive_pct: float | None
    efficiency: float | None


class PlayerProfileRead(BaseModel):
    team_id: int
    number: int
    last_name: str
    first_name: str
    position: str
    discipline: str
    season: SeasonRead | None
    career: CareerStatsRead
    by_season: list[SeasonBreakdownRead]
    attack_tendencies: list[ZoneTendencyRead]
    serve_tendencies: list[ZoneTendencyRead]
