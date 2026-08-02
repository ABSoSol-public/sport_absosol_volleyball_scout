import pytest

from app.engine.scout_code import ScoutCodeError, parse_action, parse_action_lenient


def test_parse_minimal_home_code() -> None:
    action = parse_action("5SQ=")
    assert action.side == "home"
    assert action.player_number == 5
    assert action.skill == "S"
    assert action.hit_type == "Q"
    assert action.evaluation == "="


def test_parse_away_code_with_explicit_prefix() -> None:
    action = parse_action("a7AT#")
    assert action.side == "away"
    assert action.player_number == 7
    assert action.skill == "A"
    assert action.evaluation == "#"


def test_parse_star_prefix_and_two_digit_number() -> None:
    action = parse_action("*08RQ#")
    assert action.side == "home"
    assert action.player_number == 8
    assert action.skill == "R"


def test_parse_zones() -> None:
    action = parse_action("14AH+45")
    assert action.player_number == 14
    assert action.start_zone == 4
    assert action.end_zone == 5


def test_lowercase_input_is_normalized() -> None:
    action = parse_action("5sq=")
    assert action.skill == "S"
    assert action.hit_type == "Q"


def test_invalid_code_raises() -> None:
    with pytest.raises(ScoutCodeError):
        parse_action("XX")
    with pytest.raises(ScoutCodeError):
        parse_action("5Z#")


def test_parse_subzone_refines_end_zone() -> None:
    action = parse_action("14AH+45B")
    assert action.start_zone == 4
    assert action.end_zone == 5
    assert action.subzone == "B"


def test_subzone_lowercase_is_normalized() -> None:
    action = parse_action("14AH+45b")
    assert action.subzone == "B"


def test_subzone_without_end_zone_raises() -> None:
    with pytest.raises(ScoutCodeError):
        parse_action("5SQ=A")


def test_lenient_parse_falls_back_to_raw_code_on_invalid_input() -> None:
    result = parse_action_lenient("XX")
    assert result["raw_code"] == "XX"
    assert result["side"] == "home"  # no */a prefix -> default_side
    assert result["player_number"] is None
    assert result["skill"] is None
    assert result["evaluation"] is None


def test_lenient_parse_still_guesses_side_from_prefix() -> None:
    assert parse_action_lenient("aXX")["side"] == "away"
    assert parse_action_lenient("*XX")["side"] == "home"
    assert parse_action_lenient("aXX", default_side="home")["side"] == "away"


def test_lenient_parse_respects_default_side_without_prefix() -> None:
    assert parse_action_lenient("XX", default_side="away")["side"] == "away"


def test_lenient_parse_matches_strict_parse_on_valid_input() -> None:
    assert parse_action_lenient("5SQ=") == parse_action("5SQ=").__dict__
