"""DB-Zugriffsschicht für Spielerprofile (Karrierestatistik über mehrere
Matches/Saisons, siehe docs/SPIELERPROFILE.md) — lädt Rohdaten aus
`scout_actions`/`rallies`/`match_sets`/`matches` und übersetzt sie in
`ProfileActionRow`-Listen für `app/engine/player_profile.py`.

Ein physischer Spieler wird über `(team_id, Player.number)` identifiziert
(dasselbe Muster wie beim DVW-Export/-Import, siehe docs/ARCHITEKTUR.md) —
`scout_actions` selbst trägt keine `player_id`-FK, nur `side` +
`player_number`; welches Team „home"/„away" war, kommt aus dem jeweiligen
`Match`.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.player_profile import ProfileActionRow
from app.models import Match, MatchSet, Rally, ScoutAction


@dataclass
class PlayerActionQuery:
    team_id: int
    number: int
    discipline: str | None = None
    season_id: int | None = None


def load_profile_actions(db: Session, query: PlayerActionQuery) -> list[ProfileActionRow]:
    stmt = (
        select(
            Match.id,
            Match.season_id,
            ScoutAction.skill,
            ScoutAction.evaluation,
            ScoutAction.start_zone,
            ScoutAction.end_zone,
        )
        .select_from(ScoutAction)
        .join(Rally, ScoutAction.rally_id == Rally.id)
        .join(MatchSet, Rally.set_id == MatchSet.id)
        .join(Match, MatchSet.match_id == Match.id)
        .where(ScoutAction.player_number == query.number)
        .where(
            ((Match.home_team_id == query.team_id) & (ScoutAction.side == "home"))
            | ((Match.away_team_id == query.team_id) & (ScoutAction.side == "away"))
        )
    )
    if query.discipline is not None:
        stmt = stmt.where(Match.discipline == query.discipline)
    if query.season_id is not None:
        stmt = stmt.where(Match.season_id == query.season_id)

    return [
        ProfileActionRow(
            match_id=match_id,
            season_id=season_id,
            skill=skill,
            evaluation=evaluation,
            start_zone=start_zone,
            end_zone=end_zone,
        )
        for match_id, season_id, skill, evaluation, start_zone, end_zone in db.execute(stmt).all()
    ]
