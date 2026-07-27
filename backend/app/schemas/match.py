from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.team import TeamRead


class MatchCreate(BaseModel):
    match_date: date
    competition: str = Field(default="", max_length=120)
    home_team_id: int
    away_team_id: int
    best_of: int = Field(default=5, ge=1, le=9)
    points_per_set: int = Field(default=25, ge=1)
    tiebreak_points: int = Field(default=15, ge=1)
    substitutions_per_set: int = Field(default=6, ge=0)
    timeouts_per_set: int = Field(default=2, ge=0)


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_date: date
    competition: str
    status: str
    best_of: int
    points_per_set: int
    tiebreak_points: int
    substitutions_per_set: int
    timeouts_per_set: int
    home_team: TeamRead
    away_team: TeamRead
