"""Saisons (Jul.-Jun., siehe app/seasons.py) — nur lesend; angelegt werden sie
ausschließlich automatisch beim Match-Anlegen/-Import (`get_or_create_season`).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Season
from app.schemas.season import SeasonRead

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("", response_model=list[SeasonRead])
def list_seasons(db: Session = Depends(get_db)) -> list[Season]:
    return list(db.scalars(select(Season).order_by(Season.start_date.desc())))
