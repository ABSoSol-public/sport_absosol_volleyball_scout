import pytest

from app.engine import MatchEngine, Rules, RuleViolation

HOME = [1, 2, 3, 4, 5, 6]
AWAY = [11, 12, 13, 14, 15, 16]


def start_set(engine: MatchEngine, serving: str = "home") -> None:
    engine.apply_event(
        "start_set", {"serving": serving, "home_lineup": HOME, "away_lineup": AWAY}
    )


def win_set(engine: MatchEngine, winner: str, points: int = 25) -> None:
    for _ in range(points):
        engine.apply_event("rally", {"winner": winner})
    assert engine.current_set is not None and engine.current_set.finished


def test_rally_for_serving_team_keeps_serve_and_rotation() -> None:
    engine = MatchEngine()
    start_set(engine, "home")
    engine.apply_event("rally", {"winner": "home"})
    state = engine.state()
    assert state["current_set"]["points"] == {"home": 1, "away": 0}
    assert state["current_set"]["serving"] == "home"
    assert state["current_set"]["lineups"]["home"] == HOME  # keine Rotation


def test_side_out_rotates_receiving_team_clockwise() -> None:
    engine = MatchEngine()
    start_set(engine, "home")
    engine.apply_event("rally", {"winner": "away"})
    state = engine.state()
    assert state["current_set"]["serving"] == "away"
    # Zone-2-Spieler (Index 1) rückt zum Aufschlag in Zone 1
    assert state["current_set"]["lineups"]["away"] == [12, 13, 14, 15, 16, 11]
    assert state["current_set"]["lineups"]["home"] == HOME


def test_set_needs_two_point_lead() -> None:
    engine = MatchEngine()
    start_set(engine)
    for _ in range(24):
        engine.apply_event("rally", {"winner": "home"})
        engine.apply_event("rally", {"winner": "away"})
    # 24:24 — der nächste Punkt beendet den Satz noch nicht
    engine.apply_event("rally", {"winner": "home"})
    assert not engine.current_set.finished
    engine.apply_event("rally", {"winner": "home"})
    assert engine.current_set.finished
    assert engine.sets_won == {"home": 1, "away": 0}


def test_match_ends_after_three_set_wins_and_blocks_further_events() -> None:
    engine = MatchEngine()
    for _ in range(3):
        start_set(engine)
        win_set(engine, "home")
    assert engine.match_finished
    with pytest.raises(RuleViolation):
        start_set(engine)


def test_fifth_set_uses_tiebreak_target() -> None:
    engine = MatchEngine()
    for winner in ("home", "away", "home", "away"):
        start_set(engine)
        win_set(engine, winner)
    start_set(engine)
    win_set(engine, "home", points=15)
    assert engine.match_finished
    assert engine.set_history[-1].points == {"home": 15, "away": 0}


def test_substitution_limits_and_validation() -> None:
    engine = MatchEngine(Rules(substitutions_per_set=2))
    start_set(engine)
    engine.apply_event("substitution", {"side": "home", "player_out": 1, "player_in": 7})
    with pytest.raises(RuleViolation):
        engine.apply_event("substitution", {"side": "home", "player_out": 99, "player_in": 8})
    with pytest.raises(RuleViolation):
        engine.apply_event("substitution", {"side": "home", "player_out": 2, "player_in": 7})
    engine.apply_event("substitution", {"side": "home", "player_out": 7, "player_in": 1})
    with pytest.raises(RuleViolation):
        engine.apply_event("substitution", {"side": "home", "player_out": 2, "player_in": 9})


def test_correct_lineup_overrides_without_counting_as_substitution() -> None:
    engine = MatchEngine(Rules(substitutions_per_set=0))
    start_set(engine)
    corrected = [2, 1, 3, 4, 5, 6]
    engine.apply_event("correct_lineup", {"side": "home", "lineup": corrected})
    state = engine.state()
    assert state["current_set"]["lineups"]["home"] == corrected
    assert state["current_set"]["substitutions"]["home"] == 0


def test_correct_lineup_validates_six_unique_numbers() -> None:
    engine = MatchEngine()
    start_set(engine)
    with pytest.raises(RuleViolation):
        engine.apply_event("correct_lineup", {"side": "home", "lineup": [1, 1, 3, 4, 5, 6]})
    with pytest.raises(RuleViolation):
        engine.apply_event("correct_lineup", {"side": "home", "lineup": [1, 2, 3, 4, 5]})


def test_correct_lineup_requires_running_set() -> None:
    engine = MatchEngine()
    with pytest.raises(RuleViolation):
        engine.apply_event("correct_lineup", {"side": "home", "lineup": HOME})


def test_timeout_limit() -> None:
    engine = MatchEngine()
    start_set(engine)
    engine.apply_event("timeout", {"side": "away"})
    engine.apply_event("timeout", {"side": "away"})
    with pytest.raises(RuleViolation):
        engine.apply_event("timeout", {"side": "away"})


def test_rally_requires_running_set() -> None:
    engine = MatchEngine()
    with pytest.raises(RuleViolation):
        engine.apply_event("rally", {"winner": "home"})


def test_lineup_must_be_unique() -> None:
    engine = MatchEngine()
    with pytest.raises(RuleViolation):
        engine.apply_event(
            "start_set",
            {"serving": "home", "home_lineup": [1, 1, 3, 4, 5, 6], "away_lineup": AWAY},
        )


def test_replay_reproduces_state() -> None:
    events = [
        ("start_set", {"serving": "home", "home_lineup": HOME, "away_lineup": AWAY}),
        ("rally", {"winner": "away"}),
        ("timeout", {"side": "home"}),
        ("rally", {"winner": "away"}),
    ]
    engine = MatchEngine.replay(Rules(), events)
    state = engine.state()
    assert state["current_set"]["points"] == {"home": 0, "away": 2}
    assert state["current_set"]["timeouts"] == {"home": 1, "away": 0}
    assert state["current_set"]["serving"] == "away"
