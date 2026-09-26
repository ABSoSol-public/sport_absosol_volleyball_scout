"""Spielerprofile: Karrierestatistik über mehrere Matches/Saisons
(`.../profile`) + eine FIFA-Style Skill-Karte (`.../card`, Perzentilrang
gegen alle Spieler derselben Disziplin in der Datenbank) — siehe
docs/SPIELERPROFILE.md.

Ein physischer Spieler wird über `(team_id, Trikotnummer)` adressiert (wie
beim DVW-Export/-Import, siehe docs/ARCHITEKTUR.md) — `scout_actions` selbst
trägt keine `player_id`-FK, nur `side` + `player_number`.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.engine.disciplines import DEFAULT_DISCIPLINE, Discipline
from app.engine.player_profile import (
    CareerSkillStats,
    ProfileActionRow,
    ZoneTendency,
    aggregate_career_stats,
    attack_zone_tendencies,
    serve_zone_tendencies,
)
from app.models import Player, Season, Team
from app.player_card import compute_skill_card
from app.player_data import PlayerActionQuery, load_profile_actions
from app.schemas.player_profile import PlayerProfileRead
from app.schemas.skill_card import SkillCardRead

router = APIRouter(prefix="/players", tags=["players"])


def _load_player(db: Session, team_id: int, number: int) -> Player:
    if db.get(Team, team_id) is None:
        raise HTTPException(404, "Team nicht gefunden.")
    player = db.scalar(select(Player).where(Player.team_id == team_id, Player.number == number))
    if player is None:
        raise HTTPException(404, f"Spieler Nr. {number} nicht im Kader gefunden.")
    return player


def _load_season_or_404(db: Session, season_id: int | None) -> Season | None:
    if season_id is None:
        return None
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(404, "Saison nicht gefunden.")
    return season


def _stats_dict(stats: CareerSkillStats) -> dict:
    return {
        "serve": {"total": stats.serve.total, "errors": stats.serve.errors, "aces": stats.serve.aces},
        "reception": {
            "total": stats.reception.total,
            "errors": stats.reception.errors,
            "positive": stats.reception.positive,
            "perfect": stats.reception.perfect,
            "positive_pct": stats.reception.positive_pct,
            "perfect_pct": stats.reception.perfect_pct,
        },
        "attack": {
            "total": stats.attack.total,
            "errors": stats.attack.errors,
            "blocked": stats.attack.blocked,
            "kills": stats.attack.kills,
            "efficiency": stats.attack.efficiency,
            "kill_pct": stats.attack.kill_pct,
        },
        "block": {"total": stats.block.total, "points": stats.block.points},
        "matches": stats.matches,
        "actions": stats.actions,
    }


def _tendency_dict(t: ZoneTendency) -> dict:
    return {
        "start_zone": t.start_zone,
        "end_zone": t.end_zone,
        "attempts": t.attempts,
        "positive": t.positive,
        "errors": t.errors,
        "blocked": t.blocked,
        "positive_pct": t.positive_pct,
        "efficiency": t.efficiency,
    }


@router.get("/{team_id}/{number}/profile", response_model=PlayerProfileRead)
def get_player_profile(
    team_id: int,
    number: int,
    discipline: Discipline = DEFAULT_DISCIPLINE,
    season_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    player = _load_player(db, team_id, number)
    season = _load_season_or_404(db, season_id)

    rows: list[ProfileActionRow] = load_profile_actions(
        db,
        PlayerActionQuery(
            team_id=team_id, number=number, discipline=discipline.value, season_id=season_id
        ),
    )
    career = aggregate_career_stats(rows)

    by_season_actions: dict[int, list[ProfileActionRow]] = {}
    for row in rows:
        if row.season_id is not None:
            by_season_actions.setdefault(row.season_id, []).append(row)
    seasons_by_id = (
        {
            s.id: s
            for s in db.scalars(select(Season).where(Season.id.in_(by_season_actions.keys())))
        }
        if by_season_actions
        else {}
    )
    by_season = [
        {"season": seasons_by_id[sid], "stats": _stats_dict(aggregate_career_stats(actions))}
        for sid, actions in sorted(
            by_season_actions.items(), key=lambda kv: seasons_by_id[kv[0]].start_date, reverse=True
        )
    ]

    return {
        "team_id": team_id,
        "number": number,
        "last_name": player.last_name,
        "first_name": player.first_name,
        "position": player.position,
        "discipline": discipline.value,
        "season": season,
        "career": _stats_dict(career),
        "by_season": by_season,
        "attack_tendencies": [_tendency_dict(t) for t in attack_zone_tendencies(rows)],
        "serve_tendencies": [_tendency_dict(t) for t in serve_zone_tendencies(rows)],
    }


@router.get("/{team_id}/{number}/card", response_model=SkillCardRead)
def get_player_skill_card(
    team_id: int,
    number: int,
    discipline: Discipline = DEFAULT_DISCIPLINE,
    season_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    _load_player(db, team_id, number)
    season = _load_season_or_404(db, season_id)

    card = compute_skill_card(db, team_id, number, discipline.value, season_id)
    return {
        "team_id": card.team_id,
        "number": card.number,
        "discipline": card.discipline,
        "season": season,
        "categories": {
            name: {
                "metric": c.metric,
                "rating": c.rating,
                "sample_size": c.sample_size,
                "population_size": c.population_size,
            }
            for name, c in card.categories.items()
        },
        "overall": card.overall,
    }
