from pydantic import BaseModel

from app.schemas.season import SeasonRead


class SkillCategoryRead(BaseModel):
    metric: float | None
    rating: float | None
    sample_size: int
    population_size: int


class SkillCardRead(BaseModel):
    team_id: int
    number: int
    discipline: str
    season: SeasonRead | None
    categories: dict[str, SkillCategoryRead]
    overall: float | None
