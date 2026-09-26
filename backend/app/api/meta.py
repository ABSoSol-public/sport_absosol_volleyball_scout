"""Stammdaten-Endpunkte ohne eigene DB-Tabelle (aktuell: Disziplin-Presets).

Eigener Router statt Anhängen an `matches.py`, um Pfadkollisionen mit
`GET /matches/{match_id}` zu vermeiden (ein literales `/matches/disciplines`
müsste sonst vor der parametrisierten Route registriert werden).
"""

from fastapi import APIRouter

from app.engine.disciplines import DISCIPLINE_PRESETS
from app.schemas.meta import DisciplinePresetRead

router = APIRouter(prefix="/disciplines", tags=["meta"])


@router.get("", response_model=list[DisciplinePresetRead])
def list_disciplines() -> list[DisciplinePresetRead]:
    return [
        DisciplinePresetRead(code=code.value, **preset.__dict__)
        for code, preset in DISCIPLINE_PRESETS.items()
    ]
