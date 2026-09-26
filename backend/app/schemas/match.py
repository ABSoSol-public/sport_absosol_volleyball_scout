from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.engine.disciplines import DEFAULT_DISCIPLINE, Discipline
from app.schemas.team import TeamRead


class MatchCreate(BaseModel):
    match_date: date
    competition: str = Field(default="", max_length=120)
    home_team_id: int
    away_team_id: int
    # Disziplin bestimmt die Preset-Werte für alle unten folgenden Regelfelder
    # (app/engine/disciplines.py::DISCIPLINE_PRESETS) — jedes Feld bleibt aber
    # explizit überschreibbar: `None` heißt "Preset-Wert übernehmen", ein
    # gesetzter Wert überschreibt ihn (aufgelöst in app/api/matches.py::create_match).
    discipline: Discipline = DEFAULT_DISCIPLINE
    players_on_court: int | None = Field(default=None, ge=1, le=6)
    best_of: int | None = Field(default=None, ge=1, le=9)
    points_per_set: int | None = Field(default=None, ge=1)
    tiebreak_points: int | None = Field(default=None, ge=1)
    substitutions_per_set: int | None = Field(default=None, ge=0)
    timeouts_per_set: int | None = Field(default=None, ge=0)


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_date: date
    competition: str
    status: str
    discipline: str
    players_on_court: int
    best_of: int
    points_per_set: int
    tiebreak_points: int
    substitutions_per_set: int
    timeouts_per_set: int
    home_team: TeamRead
    away_team: TeamRead


class MatchSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    home_points: int
    away_points: int
    finished: bool
    duration_minutes: int | None
