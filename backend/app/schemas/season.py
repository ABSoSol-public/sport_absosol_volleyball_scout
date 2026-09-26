from datetime import date

from pydantic import BaseModel, ConfigDict


class SeasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    start_date: date
    end_date: date
