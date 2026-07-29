"""Import einer geparsten DVW-Datei in das Domänenmodell.

Befüllt den Analyse-Strang (`matches` → `match_sets` → `rallies` →
`scout_actions`). Rally-Grenzen sind die Punktcodes (`*pXX:YY`/`apXX:YY`);
Aufschlagseite ist die Seite des ersten Serve-Codes im Ballwechsel (Fallback:
Gewinner des vorherigen Ballwechsels). Automatik-/Verwaltungscodes (`z`, `P`,
`c`, `T`, `$$`, `**Nset`) werden übersprungen, bleiben aber implizit über die
Punktestände abgebildet.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dvw.parser import DvwFile, DvwPlayer, DvwTeam
from app.models import Match, MatchSet, Player, Rally, ScoutAction, Team


@dataclass
class ImportResult:
    match: Match
    teams_created: int
    players_created: int
    sets_created: int
    rallies_created: int
    actions_created: int


def _get_or_create_team(db: Session, data: DvwTeam) -> tuple[Team, bool]:
    team = db.scalar(select(Team).where(Team.code == data.code))
    if team is None:
        team = db.scalar(select(Team).where(Team.name == data.name))
    if team is not None:
        return team, False
    team = Team(code=data.code, name=data.name)
    db.add(team)
    db.flush()
    return team, True


def _ensure_players(db: Session, team: Team, players: list[DvwPlayer]) -> int:
    existing = {
        p.number for p in db.scalars(select(Player).where(Player.team_id == team.id))
    }
    created = 0
    for entry in players:
        if entry.number in existing:
            continue
        db.add(
            Player(
                team_id=team.id,
                number=entry.number,
                last_name=entry.last_name,
                first_name=entry.first_name,
                is_libero=entry.is_libero,
            )
        )
        created += 1
        existing.add(entry.number)
    return created


def import_dvw(db: Session, parsed: DvwFile) -> ImportResult:
    home_team, home_new = _get_or_create_team(db, parsed.home_team)
    away_team, away_new = _get_or_create_team(db, parsed.away_team)
    players_created = _ensure_players(db, home_team, parsed.home_players)
    players_created += _ensure_players(db, away_team, parsed.away_players)

    match = Match(
        match_date=parsed.match_date or date.today(),
        competition=parsed.competition,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        status="finished",
    )
    db.add(match)
    db.flush()

    sets_by_number: dict[int, MatchSet] = {}
    for entry in parsed.sets:
        if entry.final_score is None:
            continue
        match_set = MatchSet(
            match_id=match.id,
            number=entry.number,
            home_points=entry.final_score[0],
            away_points=entry.final_score[1],
            finished=True,
            duration_minutes=entry.duration_minutes,
        )
        db.add(match_set)
        sets_by_number[entry.number] = match_set
    db.flush()

    rallies = actions_total = 0
    pending: list = []  # Aktionscodes des laufenden Ballwechsels
    rally_number = 0
    current_set = None
    last_winner: str | None = None

    for row in parsed.scout_rows:
        if current_set != row.set_number:
            current_set = row.set_number
            rally_number = 0
            pending = []
            last_winner = None

        if row.skill is not None:
            pending.append(row)
            continue

        if row.point_side is None:
            continue  # Verwaltungscode

        match_set = sets_by_number.get(row.set_number)
        if match_set is None:
            pending = []
            continue

        serving = next((r.side for r in pending if r.skill == "S"), None) or (
            last_winner or "home"
        )
        rally_number += 1
        rally = Rally(
            set_id=match_set.id,
            number=rally_number,
            serving_side=serving,
            winner_side=row.point_side,
            home_score_after=row.home_score or 0,
            away_score_after=row.away_score or 0,
            home_setter_position=row.home_setter_position,
            away_setter_position=row.away_setter_position,
        )
        db.add(rally)
        db.flush()
        for seq, action in enumerate(pending, start=1):
            db.add(
                ScoutAction(
                    rally_id=rally.id,
                    seq=seq,
                    raw_code=action.raw_code[:40],
                    side=action.side,
                    player_number=action.player_number,
                    skill=action.skill,
                    hit_type=action.hit_type,
                    evaluation=action.evaluation,
                    start_zone=action.start_zone,
                    end_zone=action.end_zone,
                )
            )
        actions_total += len(pending)
        rallies += 1
        last_winner = row.point_side
        pending = []

    db.commit()
    return ImportResult(
        match=match,
        teams_created=int(home_new) + int(away_new),
        players_created=players_created,
        sets_created=len(sets_by_number),
        rallies_created=rallies,
        actions_created=actions_total,
    )
