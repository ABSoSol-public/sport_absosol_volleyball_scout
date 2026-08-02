"""Live-Scouting-Endpunkte.

Quelle der Wahrheit ist die Event-Tabelle `live_events` (Event-Sourcing).
Jeder Request lädt die Events des Matches, spielt sie in der `MatchEngine` nach,
validiert das neue Event gegen die Volleyball-Regeln und persistiert es erst dann.
Undo entfernt das letzte Event — identisch zum "Undo End Rally" im DV4-Vorbild.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.db.session import get_db
from app.engine import MatchEngine, Rules, RuleViolation
from app.engine.scout_code import ScoutCodeError, parse_action
from app.models import LiveEvent, Match, User
from app.schemas.live import (
    HistoryActionsUpdate,
    LineupCorrectionRequest,
    RallyRequest,
    StartSetRequest,
    SubstitutionRequest,
    TimeoutRequest,
)

router = APIRouter(prefix="/matches/{match_id}/live", tags=["live"])


def _load_match(match_id: int, db: Session) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "Match nicht gefunden.")
    return match


def _rules(match: Match) -> Rules:
    return Rules(
        best_of=match.best_of,
        points_per_set=match.points_per_set,
        tiebreak_points=match.tiebreak_points,
        substitutions_per_set=match.substitutions_per_set,
        timeouts_per_set=match.timeouts_per_set,
    )


def _events(match_id: int, db: Session) -> list[LiveEvent]:
    return list(
        db.scalars(
            select(LiveEvent).where(LiveEvent.match_id == match_id).order_by(LiveEvent.seq)
        )
    )


def _rebuild(match: Match, events: list[LiveEvent]) -> MatchEngine:
    return MatchEngine.replay(_rules(match), [(e.event_type, e.payload) for e in events])


def _append_event(
    match: Match, event_type: str, payload: dict[str, Any], db: Session
) -> dict[str, Any]:
    events = _events(match.id, db)
    engine = _rebuild(match, events)
    try:
        engine.apply_event(event_type, payload)
    except RuleViolation as exc:
        raise HTTPException(422, str(exc)) from exc

    db.add(
        LiveEvent(
            match_id=match.id,
            seq=events[-1].seq + 1 if events else 1,
            event_type=event_type,
            payload=payload,
        )
    )
    match.status = "finished" if engine.match_finished else "live"
    db.commit()
    return engine.state()


@router.get("/state")
def get_state(match_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    match = _load_match(match_id, db)
    return _rebuild(match, _events(match_id, db)).state()


def _score_snapshot(engine: MatchEngine) -> tuple[int | None, int | None, int | None]:
    """(set number, home points, away points) right after the last applied event."""
    current = engine.current_set
    if current is not None:
        return current.number, current.points["home"], current.points["away"]
    if engine.set_history:
        finished = engine.set_history[-1]
        return finished.number, finished.points["home"], finished.points["away"]
    return None, None, None


@router.get("/history")
def get_history(match_id: int, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Chronological log of all events, for the scout-code history table in the frontend.

    Builds the score for each event via incremental replay (analogous to the
    DVW `sp_home/guest_setter_pos` principle: every row carries its own
    context instead of it being back-calculated from the final state).
    """
    match = _load_match(match_id, db)
    engine = MatchEngine(_rules(match))
    rows: list[dict[str, Any]] = []
    for event in _events(match_id, db):
        engine.apply_event(event.event_type, event.payload)
        set_number, home_score, away_score = _score_snapshot(engine)
        row: dict[str, Any] = {
            "seq": event.seq,
            "event_type": event.event_type,
            "created_at": event.created_at,
            "set_number": set_number,
            "home_score": home_score,
            "away_score": away_score,
            "payload": event.payload,
        }
        if event.event_type == "rally":
            row["winner"] = event.payload.get("winner")
            row["actions"] = event.payload.get("actions", [])
        rows.append(row)
    return rows


@router.patch("/history/{seq}")
def correct_history_actions(
    match_id: int, seq: int, data: HistoryActionsUpdate, db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> dict[str, Any]:
    """Retroactive correction of the scout codes of an already-recorded rally.

    Deliberately changes only the action list (description), never `winner` —
    score/rotation depend exclusively on `winner` (see
    `MatchEngine._on_rally`), so this correction doesn't need a replay.
    """
    _load_match(match_id, db)
    event = db.scalar(
        select(LiveEvent).where(LiveEvent.match_id == match_id, LiveEvent.seq == seq)
    )
    if event is None:
        raise HTTPException(404, "Eintrag nicht gefunden.")
    if event.event_type != "rally":
        raise HTTPException(422, "Nur Ballwechsel-Einträge mit Scout-Codes sind bearbeitbar.")

    actions: list[dict[str, Any]] = []
    for code in data.actions:
        try:
            actions.append(parse_action(code).__dict__)
        except (ScoutCodeError, IndexError) as exc:
            raise HTTPException(422, f"Scout-Code {code!r}: {exc}") from exc

    event.payload = {**event.payload, "actions": actions}
    db.commit()
    return {"seq": event.seq, "actions": actions}


@router.post("/set")
def start_set(match_id: int, data: StartSetRequest, db: Session = Depends(get_db), _writer: User = Depends(require_writer)) -> dict[str, Any]:
    match = _load_match(match_id, db)
    return _append_event(match, "start_set", data.model_dump(), db)


@router.post("/rally")
def record_rally(match_id: int, data: RallyRequest, db: Session = Depends(get_db), _writer: User = Depends(require_writer)) -> dict[str, Any]:
    match = _load_match(match_id, db)
    actions: list[dict[str, Any]] = []
    for code in data.actions:
        try:
            actions.append(parse_action(code).__dict__)
        except (ScoutCodeError, IndexError) as exc:
            raise HTTPException(422, f"Scout-Code {code!r}: {exc}") from exc
    return _append_event(match, "rally", {"winner": data.winner, "actions": actions}, db)


@router.post("/substitution")
def record_substitution(
    match_id: int, data: SubstitutionRequest, db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> dict[str, Any]:
    match = _load_match(match_id, db)
    return _append_event(match, "substitution", data.model_dump(), db)


@router.post("/timeout")
def record_timeout(
    match_id: int, data: TimeoutRequest, db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> dict[str, Any]:
    match = _load_match(match_id, db)
    return _append_event(match, "timeout", data.model_dump(), db)


@router.post("/lineup-correction")
def correct_lineup(
    match_id: int, data: LineupCorrectionRequest, db: Session = Depends(get_db),
    _writer: User = Depends(require_writer),
) -> dict[str, Any]:
    match = _load_match(match_id, db)
    return _append_event(match, "correct_lineup", data.model_dump(), db)


@router.post("/undo")
def undo_last_event(
    match_id: int, db: Session = Depends(get_db), _writer: User = Depends(require_writer)
) -> dict[str, Any]:
    match = _load_match(match_id, db)
    events = _events(match_id, db)
    if not events:
        raise HTTPException(422, "Kein Event vorhanden, das rückgängig gemacht werden kann.")
    db.delete(events[-1])
    engine = _rebuild(match, events[:-1])
    match.status = (
        "finished" if engine.match_finished else ("live" if len(events) > 1 else "scheduled")
    )
    db.commit()
    return engine.state()
