from pydantic import BaseModel, ConfigDict, Field


class PlayerCreate(BaseModel):
    number: int = Field(ge=0, le=99)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(default="", max_length=80)
    position: str = Field(default="", max_length=20)
    is_libero: bool = False


class PlayerRead(PlayerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeamCreate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str = Field(min_length=1, max_length=120)


class TeamRead(TeamCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeamDetail(TeamRead):
    players: list[PlayerRead] = []
