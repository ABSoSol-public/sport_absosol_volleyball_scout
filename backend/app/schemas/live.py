from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["home", "away"]


class StartSetRequest(BaseModel):
    serving: Side
    # Länge nicht fix auf 6 begrenzt (Mehrfach-Formate, z. B. Beach 2:2/
    # Jugend-Kleinfeld 3:3/4:4, siehe app/engine/disciplines.py) — die exakte
    # Spieleranzahl je `Match.players_on_court` prüft `MatchEngine` (422 bei
    # Abweichung), nicht das Schema.
    home_lineup: list[int] = Field(min_length=1)
    away_lineup: list[int] = Field(min_length=1)


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
    lineup: list[int] = Field(min_length=1)  # exakte Anzahl prüft MatchEngine, siehe oben


class HistoryActionsUpdate(BaseModel):
    # Correction of an already-recorded rally: same free-text code style as
    # direct entry (RallyRequest.actions), replaces the whole action list of
    # that rally. `winner`/score are left untouched — only the scout codes
    # (description), not the match result, are being corrected. May be empty
    # (e.g. removing the last remaining action of a rally), same as
    # RallyRequest.actions.
    actions: list[str] = []
