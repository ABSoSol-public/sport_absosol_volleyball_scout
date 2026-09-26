from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PlayerPosition(str, Enum):
    """Standard-Positionen (5-1-System) + Universal, siehe docs/ARCHITEKTUR.md."""

    SETTER = "Zuspieler"
    OUTSIDE = "Außenangreifer"
    OPPOSITE = "Diagonalangreifer"
    MIDDLE = "Mittelblocker"
    LIBERO = "Libero"
    UNIVERSAL = "Universalspieler"


class SetterSystem(str, Enum):
    """Zuspielsystem des Teams (rein informativ, siehe docs/SPIELFORMATE.md).

    Beeinflusst **keine** Engine-Logik — `Player.is_primary_setter` +
    dessen Fallback auf die Position "Zuspieler" (`app/engine/rotation.py::
    setter_zone`) bilden bereits alle vier Systeme korrekt ab: bei 5-1/6-2
    steht ohnehin nie mehr als ein Zuspieler gleichzeitig auf dem Feld
    (Rotationsschema), bei 4-2 können beide gleichzeitig auf dem Feld stehen
    — genau dafür existiert `is_primary_setter` als Tie-Breaker. Bei 6-6
    (kein fester Zuspieler) bleibt die Zone einfach leer/„–", ebenfalls
    korrekt. Das Feld dient nur der Dokumentation/Anzeige im Kader.
    """

    ONE_FIVE = "5-1"
    SIX_TWO = "6-2"
    FOUR_TWO = "4-2"
    SIX_SIX = "6-6"


class PlayerCreate(BaseModel):
    number: int = Field(ge=0, le=99)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(default="", max_length=80)
    position: PlayerPosition | None = None
    is_libero: bool = False
    is_youth_player: bool = False
    # Referenz-Zuspieler fürs Rotationscode (Z1–Z6): nur relevant, wenn ein Team
    # zwei Zuspieler im Kader führt (z. B. 6-2-System) — legt fest, wessen
    # aktuelle Zone den Rotationscode bestimmt. Höchstens einer pro Team
    # (siehe api/teams.py: Setzen entfernt das Flag beim bisherigen Träger).
    is_primary_setter: bool = False


class PlayerUpdate(BaseModel):
    number: int = Field(ge=0, le=99)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(default="", max_length=80)
    position: PlayerPosition | None = None
    is_libero: bool = False
    is_youth_player: bool = False
    is_primary_setter: bool = False


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    last_name: str
    first_name: str
    position: str
    is_libero: bool
    is_youth_player: bool
    is_primary_setter: bool


class TeamCreate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str = Field(min_length=1, max_length=120)
    setter_system: SetterSystem | None = None


class TeamUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=8)
    name: str = Field(min_length=1, max_length=120)
    setter_system: SetterSystem | None = None


class TeamRead(TeamCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TeamDetail(TeamRead):
    players: list[PlayerRead] = []
