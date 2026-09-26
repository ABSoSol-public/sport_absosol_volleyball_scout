"""Ableitung des Analyse-Strangs (`match_sets`/`rallies`/`scout_actions`) aus den
`live_events` eines Matches (Roadmap 2.7).

Vorher lieferte ausschließlich ein DVW-Import den Analyse-Strang; live-
gescoutete Matches schrieben nur `live_events` und blieben deshalb ohne
Statistikauswertung und ohne Anzeige im Match-Browser
(`MatchDetailView.vue` zeigte einen „noch keine Analyse-Daten"-Hinweis statt
einer leeren/irreführenden Ansicht, siehe docs/ARCHITEKTUR.md). Diese Funktion
schließt die Lücke: sie nutzt dieselbe Replay-Logik wie
`app/dvw/exporter.py::build_export_from_live_events`, erzeugt daraus aber
direkt ORM-Zeilen statt einer DVW-Zwischendarstellung.

Aufgerufen nach jeder Zustandsänderung des Live-Strangs
(`app/api/live.py::_append_event`/`undo_last_event`) sowie als Backfill beim
Lesen (`app/api/matches.py`, für Matches, die vor dieser Version
fertig-/teilgescoutet wurden). Idempotent und immer ein Voll-Rebuild:
bestehende `match_sets` (cascade löscht `rallies`/`scout_actions`) werden vor
dem Neuaufbau gelöscht — konsistent mit dem übrigen Event-Sourcing-Prinzip
des Projekts (Zustand entsteht immer per vollständigem Replay, nie
inkrementell fortgeschrieben), und günstig genug für die hier üblichen
Match-Größenordnungen (siehe „Rebuild-Kosten" in docs/ARCHITEKTUR.md).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.match_engine import MatchEngine, Rules
from app.engine.rotation import setter_zone
from app.models import LiveEvent, Match, MatchSet, Player, Rally, ScoutAction


def _rules(match: Match) -> Rules:
    return Rules(
        best_of=match.best_of,
        points_per_set=match.points_per_set,
        tiebreak_points=match.tiebreak_points,
        substitutions_per_set=match.substitutions_per_set,
        timeouts_per_set=match.timeouts_per_set,
    )


def sync_from_live_events(db: Session, match: Match) -> None:
    for existing in db.scalars(select(MatchSet).where(MatchSet.match_id == match.id)):
        db.delete(existing)
    db.flush()

    events = list(
        db.scalars(
            select(LiveEvent).where(LiveEvent.match_id == match.id).order_by(LiveEvent.seq)
        )
    )
    if not events:
        return

    home_roster = list(db.scalars(select(Player).where(Player.team_id == match.home_team_id)))
    away_roster = list(db.scalars(select(Player).where(Player.team_id == match.away_team_id)))

    engine = MatchEngine(_rules(match))
    sets_by_number: dict[int, MatchSet] = {}
    rally_number_by_set: dict[int, int] = {}

    for event in events:
        if event.event_type == "rally":
            # Aufstellung/Satznummer/Aufschlagseite *vor* dieser Aktion — der
            # Zustand, unter dem der Ballwechsel tatsächlich gespielt wurde
            # (`apply_event` rotiert bei Side-Out sofort weiter).
            current = engine.current_set
            lineup_home = list(current.lineups["home"]) if current else []
            lineup_away = list(current.lineups["away"]) if current else []
            set_number = current.number if current else 1
            serving = current.serving if current else "home"

        engine.apply_event(event.event_type, event.payload)

        if event.event_type != "rally":
            continue

        current_now = engine.current_set
        home_after = current_now.points["home"] if current_now else 0
        away_after = current_now.points["away"] if current_now else 0

        match_set = sets_by_number.get(set_number)
        if match_set is None:
            match_set = MatchSet(match_id=match.id, number=set_number)
            db.add(match_set)
            db.flush()
            sets_by_number[set_number] = match_set
            rally_number_by_set[set_number] = 0

        rally_number_by_set[set_number] += 1
        rally = Rally(
            set_id=match_set.id,
            number=rally_number_by_set[set_number],
            serving_side=serving,
            winner_side=event.payload["winner"],
            home_score_after=home_after,
            away_score_after=away_after,
            home_setter_position=setter_zone(home_roster, lineup_home),
            away_setter_position=setter_zone(away_roster, lineup_away),
        )
        db.add(rally)
        db.flush()
        for seq, action in enumerate(event.payload.get("actions", []), start=1):
            db.add(
                ScoutAction(
                    rally_id=rally.id,
                    seq=seq,
                    raw_code=action["raw_code"][:40],
                    side=action["side"],
                    player_number=action.get("player_number"),
                    skill=action.get("skill"),
                    hit_type=action.get("hit_type"),
                    evaluation=action.get("evaluation"),
                    start_zone=action.get("start_zone"),
                    end_zone=action.get("end_zone"),
                    subzone=action.get("subzone"),
                    created_at=event.created_at,
                )
            )
        match_set.home_points = home_after
        match_set.away_points = away_after

    for set_state in engine.set_history:
        finished_set = sets_by_number.get(set_state.number)
        if finished_set is not None:
            finished_set.finished = True
