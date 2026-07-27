from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Match, Team
from app.schemas.match import MatchCreate, MatchRead

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchRead])
def list_matches(db: Session = Depends(get_db)) -> list[Match]:
    return list(db.scalars(select(Match).order_by(Match.match_date.desc(), Match.id.desc())))


@router.post("", response_model=MatchRead, status_code=201)
def create_match(data: MatchCreate, db: Session = Depends(get_db)) -> Match:
    for team_id in (data.home_team_id, data.away_team_id):
        if db.get(Team, team_id) is None:
            raise HTTPException(404, f"Team {team_id} nicht gefunden.")
    if data.home_team_id == data.away_team_id:
        raise HTTPException(422, "Heim- und Gastteam müssen unterschiedlich sein.")
    match = Match(**data.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db)) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "Match nicht gefunden.")
    return match
