import pytest

from app.engine.scout_code import (
    ScoutCodeError,
    parse_action,
    parse_action_lenient,
    parse_scout_code,
)


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


# --- Compound codes (serve+reception) ---------------------------------

def test_compound_code_matches_user_worked_example() -> None:
    # *17S14.3# : home player 17 serves zone 1->4, away player 3 receives
    # perfectly (#) -> the serve itself is implied "-" (never written).
    serve, reception = parse_scout_code("*17S14.3#")

    assert serve["raw_code"] == "*17S14.3#"
    assert serve["side"] == "home"
    assert serve["player_number"] == 17
    assert serve["skill"] == "S"
    assert serve["start_zone"] == 1
    assert serve["end_zone"] == 4
    assert serve["evaluation"] == "-"  # implied from reception "#"

    assert reception["raw_code"] == "*17S14.3#"
    assert reception["side"] == "away"  # opponent of the server
    assert reception["player_number"] == 3
    assert reception["skill"] == "R"
    assert reception["evaluation"] == "#"
    assert reception["start_zone"] is None


def test_compound_code_with_hit_type_and_away_server() -> None:
    # a3SQ16.11= : away player 3 serves (type Q) zone 1->6, home player 11
    # gets aced (=) -> serve is implied "#".
    serve, reception = parse_scout_code("a3SQ16.11=")

    assert serve["side"] == "away"
    assert serve["hit_type"] == "Q"
    assert serve["evaluation"] == "#"
    assert reception["side"] == "home"
    assert reception["player_number"] == 11
    assert reception["evaluation"] == "="


@pytest.mark.parametrize(
    ("reception_eval", "implied_serve_eval"),
    [("=", "#"), ("-", "+"), ("/", "/"), ("#", "-"), ("+", "-")],
)
def test_compound_code_reception_to_serve_mapping(
    reception_eval: str, implied_serve_eval: str
) -> None:
    serve, _reception = parse_scout_code(f"*5S14.7{reception_eval}")
    assert serve["evaluation"] == implied_serve_eval


def test_compound_code_returns_single_entry_for_non_serve_skill() -> None:
    # Attack+block/attack+dig compounds aren't decomposed (no confirmed
    # domain rules for them yet) -> falls back to the lenient raw path.
    result = parse_scout_code("8A66.9")
    assert len(result) == 1
    assert result[0]["raw_code"] == "8A66.9"
    assert result[0]["skill"] is None  # strict grammar doesn't accept "."


def test_plain_code_still_returns_single_entry() -> None:
    result = parse_scout_code("5SQ=")
    assert result == [parse_action("5SQ=").__dict__]


def test_scout_code_without_dot_is_unaffected() -> None:
    assert parse_scout_code("XX") == [parse_action_lenient("XX")]
