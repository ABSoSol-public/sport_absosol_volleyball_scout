from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Player, Team
from app.schemas.team import PlayerCreate, PlayerRead, TeamCreate, TeamDetail, TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    return list(db.scalars(select(Team).order_by(Team.name)))


@router.post("", response_model=TeamRead, status_code=201)
def create_team(data: TeamCreate, db: Session = Depends(get_db)) -> Team:
    if db.scalar(select(Team).where(Team.code == data.code)):
        raise HTTPException(409, f"Team-Code {data.code!r} existiert bereits.")
    team = Team(code=data.code, name=data.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamDetail)
def get_team(team_id: int, db: Session = Depends(get_db)) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(404, "Team nicht gefunden.")
    return team


@router.post("/{team_id}/players", response_model=PlayerRead, status_code=201)
def add_player(team_id: int, data: PlayerCreate, db: Session = Depends(get_db)) -> Player:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(404, "Team nicht gefunden.")
    exists = db.scalar(
        select(Player).where(Player.team_id == team_id, Player.number == data.number)
    )
    if exists:
        raise HTTPException(409, f"Nummer {data.number} ist im Team bereits vergeben.")
    player = Player(team_id=team_id, **data.model_dump())
    db.add(player)
    db.commit()
    db.refresh(player)
    return player
