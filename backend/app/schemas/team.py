from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PlayerPosition(str, Enum):
    """Standard-Positionen (5-1-System), siehe docs/ARCHITEKTUR.md."""

    SETTER = "Zuspieler"
    OUTSIDE = "Außenangreifer"
    OPPOSITE = "Diagonalangreifer"
    MIDDLE = "Mittelblocker"
    LIBERO = "Libero"


class PlayerCreate(BaseModel):
    number: int = Field(ge=0, le=99)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(default="", max_length=80)
    position: PlayerPosition | None = None
    is_libero: bool = False
    is_youth_player: bool = False


class PlayerUpdate(BaseModel):
    number: int = Field(ge=0, le=99)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(default="", max_length=80)
    position: PlayerPosition | None = None
    is_libero: bool = False
    is_youth_player: bool = False


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    last_name: str
    first_name: str
    position: str
    is_libero: bool
    is_youth_player: bool


class TeamCreate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str = Field(min_length=1, max_length=120)


class TeamUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str = Field(min_length=1, max_length=120)


class TeamRead(TeamCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeamDetail(TeamRead):
    players: list[PlayerRead] = []
