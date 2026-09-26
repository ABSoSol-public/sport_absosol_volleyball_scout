from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analyse_sync import sync_from_live_events
from app.api.deps import require_writer
from app.db.session import get_db
from app.dvw.exporter import build_export_match, render_dvw
from app.engine.disciplines import DISCIPLINE_PRESETS
from app.engine.statistics import ActionRow, RallyRow, compute_match_statistics
from app.models import LiveEvent, Match, MatchSet, Rally, Team, User
from app.schemas.match import MatchCreate, MatchRead, MatchSetRead
from app.schemas.statistics import MatchStatisticsRead

router = APIRouter(prefix="/matches", tags=["matches"])


def _ensure_analyse_strang_synced(match_id: int, db: Session) -> None:
    """Backfill für Matches, deren `live_events` noch nie in den Analyse-Strang
    übernommen wurden (gescoutet, bevor `app/api/live.py` `sync_from_live_events`
    nach jedem Event aufrief — Roadmap 2.7). Ein rein lesender Zugriff
    (`GET .../sets`, `GET .../statistics`) darf hier trotzdem schreiben: das
    Ergebnis ist deterministisch aus `live_events` abgeleitet, kein neuer
    Nutzerinput. Matches mit vorhandenen DVW-Importdaten sind bereits
    synchron (kein passendes `live_events`), einmal fertiggescoutete Matches
    bleiben es ab dem ersten Sync ebenfalls, da jedes neue Event erneut
    synct — dieser Pfad greift also nur einmalig pro Altdaten-Match.
    """
    has_sets = db.scalar(select(MatchSet.id).where(MatchSet.match_id == match_id).limit(1))
    if has_sets is not None:
        return
    has_events = db.scalar(select(LiveEvent.id).where(LiveEvent.match_id == match_id).limit(1))
    if has_events is None:
        return
    match = db.get(Match, match_id)
    if match is None:
        return
    sync_from_live_events(db, match)
    db.commit()


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

    preset = DISCIPLINE_PRESETS[data.discipline]
    fields = data.model_dump()
    for rule_field in (
        "players_on_court",
        "best_of",
        "points_per_set",
        "tiebreak_points",
        "substitutions_per_set",
        "timeouts_per_set",
    ):
        if fields[rule_field] is None:
            fields[rule_field] = getattr(preset, rule_field)
    fields["discipline"] = data.discipline.value
    match = Match(**fields)
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
    _ensure_analyse_strang_synced(match_id, db)
    return list(
        db.scalars(
            select(MatchSet).where(MatchSet.match_id == match_id).order_by(MatchSet.number)
        )
    )


@router.get("/{match_id}/export")
def export_match_dvw(match_id: int, db: Session = Depends(get_db)) -> Response:
    """DVW-kompatibler Export (Roadmap 2.6) — funktioniert für beide Stränge
    gleichwertig (Analyse-Strang aus DVW-Import, Live-Strang aus `live_events`),
    siehe `app/dvw/exporter.py` für Details und bekannte Einschränkungen.
    """
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "Match nicht gefunden.")
    export = build_export_match(db, match)
    if export is None:
        raise HTTPException(
            422, "Für dieses Match liegen weder Analyse- noch Live-Scouting-Daten vor."
        )
    content = render_dvw(export)
    filename = f"{export.home_team_code}_{export.away_team_code}_{match.match_date}.dvw"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{match_id}/statistics", response_model=MatchStatisticsRead)
def get_match_statistics(match_id: int, db: Session = Depends(get_db)) -> MatchStatisticsRead:
    if db.get(Match, match_id) is None:
        raise HTTPException(404, "Match nicht gefunden.")
    _ensure_analyse_strang_synced(match_id, db)

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
