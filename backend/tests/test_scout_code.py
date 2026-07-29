import pytest

from app.engine.scout_code import ScoutCodeError, parse_action


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
