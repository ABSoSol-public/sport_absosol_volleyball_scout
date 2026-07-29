from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.db.session import get_db
from app.models import Player, Team, User
from app.schemas.team import (
    PlayerCreate,
    PlayerRead,
    PlayerUpdate,
    TeamCreate,
    TeamDetail,
    TeamRead,
    TeamUpdate,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    return list(db.scalars(select(Team).order_by(Team.name)))


@router.post("", response_model=TeamRead, status_code=201)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> Team:
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


@router.patch("/{team_id}", response_model=TeamRead)
def update_team(
    team_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(404, "Team nicht gefunden.")
    other = db.scalar(select(Team).where(Team.code == data.code, Team.id != team_id))
    if other:
        raise HTTPException(409, f"Team-Code {data.code!r} existiert bereits.")
    team.code = data.code
    team.name = data.name
    db.commit()
    db.refresh(team)
    return team


@router.post("/{team_id}/players", response_model=PlayerRead, status_code=201)
def add_player(
    team_id: int,
    data: PlayerCreate,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> Player:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(404, "Team nicht gefunden.")
    exists = db.scalar(
        select(Player).where(Player.team_id == team_id, Player.number == data.number)
    )
    if exists:
        raise HTTPException(409, f"Nummer {data.number} ist im Team bereits vergeben.")
    player = Player(
        team_id=team_id,
        number=data.number,
        last_name=data.last_name,
        first_name=data.first_name,
        position=data.position or "",
        is_libero=data.is_libero,
        is_youth_player=data.is_youth_player,
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/{team_id}/players/{player_id}", response_model=PlayerRead)
def update_player(
    team_id: int,
    player_id: int,
    data: PlayerUpdate,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> Player:
    player = db.get(Player, player_id)
    if player is None or player.team_id != team_id:
        raise HTTPException(404, "Spieler nicht gefunden.")
    exists = db.scalar(
        select(Player).where(
            Player.team_id == team_id, Player.number == data.number, Player.id != player_id
        )
    )
    if exists:
        raise HTTPException(409, f"Nummer {data.number} ist im Team bereits vergeben.")
    player.number = data.number
    player.last_name = data.last_name
    player.first_name = data.first_name
    player.position = data.position or ""
    player.is_libero = data.is_libero
    player.is_youth_player = data.is_youth_player
    db.commit()
    db.refresh(player)
    return player
