from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["home", "away"]


class StartSetRequest(BaseModel):
    serving: Side
    home_lineup: list[int] = Field(min_length=6, max_length=6)
    away_lineup: list[int] = Field(min_length=6, max_length=6)


class RallyRequest(BaseModel):
    winner: Side
    # Scout-Codes im DV-Main-Code-Format (z. B. "5SQ=", "a7AT#"), optional
    actions: list[str] = []


class SubstitutionRequest(BaseModel):
    side: Side
    player_out: int
    player_in: int


class TimeoutRequest(BaseModel):
    side: Side


class LineupCorrectionRequest(BaseModel):
    side: Side
    lineup: list[int] = Field(min_length=6, max_length=6)
