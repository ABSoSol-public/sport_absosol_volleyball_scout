from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_writer
from app.db.session import get_db
from app.engine.statistics import ActionRow, RallyRow, compute_match_statistics
from app.models import Match, MatchSet, Rally, Team, User
from app.schemas.match import MatchCreate, MatchRead, MatchSetRead
from app.schemas.statistics import MatchStatisticsRead

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchRead])
def list_matches(db: Session = Depends(get_db)) -> list[Match]:
    return list(db.scalars(select(Match).order_by(Match.match_date.desc(), Match.id.desc())))


@router.post("", response_model=MatchRead, status_code=201)
def create_match(
    data: MatchCreate,
    db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> Match:
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


@router.get("/{match_id}/sets", response_model=list[MatchSetRead])
def get_match_sets(match_id: int, db: Session = Depends(get_db)) -> list[MatchSet]:
    if db.get(Match, match_id) is None:
        raise HTTPException(404, "Match nicht gefunden.")
    return list(
        db.scalars(
            select(MatchSet).where(MatchSet.match_id == match_id).order_by(MatchSet.number)
        )
    )


@router.get("/{match_id}/statistics", response_model=MatchStatisticsRead)
def get_match_statistics(match_id: int, db: Session = Depends(get_db)) -> MatchStatisticsRead:
    if db.get(Match, match_id) is None:
        raise HTTPException(404, "Match nicht gefunden.")

    rallies = db.scalars(
        select(Rally)
        .join(MatchSet)
        .where(MatchSet.match_id == match_id)
        .options(selectinload(Rally.actions))
        .order_by(MatchSet.number, Rally.number)
    )
    rally_rows = [
        RallyRow(
            serving_side=rally.serving_side,
            winner_side=rally.winner_side,
            home_setter_position=rally.home_setter_position,
            away_setter_position=rally.away_setter_position,
            actions=[
                ActionRow(
                    side=action.side,
                    player_number=action.player_number,
                    skill=action.skill,
                    evaluation=action.evaluation,
                )
                for action in rally.actions
            ],
        )
        for rally in rallies
    ]

    stats = compute_match_statistics(rally_rows)
    return MatchStatisticsRead.model_validate(
        {
            "home_players": stats.players["home"],
            "away_players": stats.players["away"],
            "home_team": stats.teams["home"],
            "away_team": stats.teams["away"],
            "home_rotations": stats.rotations["home"],
            "away_rotations": stats.rotations["away"],
        }
    )
