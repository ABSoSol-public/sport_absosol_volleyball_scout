from pydantic import BaseModel


class DisciplinePresetRead(BaseModel):
    code: str
    label: str
    players_on_court: int
    best_of: int
    points_per_set: int
    tiebreak_points: int
    substitutions_per_set: int
    timeouts_per_set: int
    has_libero: bool
    has_rotation_zones: bool
