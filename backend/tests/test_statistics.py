from fastapi.testclient import TestClient

from app.engine.statistics import ActionRow, RallyRow, compute_match_statistics
from tests.test_dvw_import import DVW_SAMPLE


def _action(side: str, number: int, skill: str, evaluation: str | None) -> ActionRow:
    return ActionRow(side=side, player_number=number, skill=skill, evaluation=evaluation)


# Fünf Ballwechsel, konstruiert um jeden Formelpfad aus engine/statistics.py
# mindestens einmal zu treffen (siehe Herleitung/Rechnung in der Session-Notiz):
# 1) Ass (Serve #)                      -> home Break, Rotation 1
# 2) Aufschlagfehler (Serve =)          -> away Side-Out, Punktquelle "opponent_errors"
# 3) Annahme perfekt + Angriffspunkt    -> home Side-Out (Rotation wechselt auf 2)
# 4) Annahmefehler                      -> home Break, Punktquelle "opponent_errors"
# 5) Angriff geblockt + Blockpunkt      -> home Break
RALLIES = [
    RallyRow(
        serving_side="home",
        winner_side="home",
        home_setter_position=1,
        away_setter_position=1,
        actions=[_action("home", 7, "S", "#")],
    ),
    RallyRow(
        serving_side="home",
        winner_side="away",
        home_setter_position=1,
        away_setter_position=1,
        actions=[_action("home", 7, "S", "=")],
    ),
    RallyRow(
        serving_side="away",
        winner_side="home",
        home_setter_position=1,
        away_setter_position=2,
        actions=[
            _action("away", 3, "S", "+"),
            _action("home", 9, "R", "#"),
            _action("home", 7, "A", "#"),
        ],
    ),
    RallyRow(
        serving_side="home",
        winner_side="home",
        home_setter_position=2,
        away_setter_position=2,
        actions=[
            _action("home", 9, "S", "+"),
            _action("away", 5, "R", "="),
        ],
    ),
    RallyRow(
        serving_side="home",
        winner_side="home",
        home_setter_position=2,
        away_setter_position=2,
        actions=[
            _action("home", 9, "S", "+"),
            _action("away", 5, "R", "+"),
            _action("away", 5, "A", "/"),
            _action("home", 7, "B", "#"),
        ],
    ),
]


def test_player_serve_reception_attack_block_stats() -> None:
    stats = compute_match_statistics(RALLIES)
    home = {p.player_number: p for p in stats.players["home"]}
    away = {p.player_number: p for p in stats.players["away"]}

    assert home[7].serve.total == 2
    assert home[7].serve.aces == 1
    assert home[7].serve.errors == 1
    assert home[7].attack.total == 1
    assert home[7].attack.kills == 1
    assert home[7].attack.efficiency == 1.0
    assert home[7].block.total == 1
    assert home[7].block.points == 1

    assert home[9].reception.total == 1
    assert home[9].reception.perfect == 1
    assert home[9].reception.positive_pct == 100.0

    assert away[5].reception.total == 2
    assert away[5].reception.errors == 1
    assert away[5].reception.positive == 1
    assert away[5].reception.positive_pct == 50.0
    assert away[5].attack.total == 1
    assert away[5].attack.blocked == 1
    assert away[5].attack.efficiency == -1.0


def test_team_side_out_break_and_point_sources() -> None:
    stats = compute_match_statistics(RALLIES)
    home_team = stats.teams["home"]
    away_team = stats.teams["away"]

    # home serviert 1,2,4,5 (4x) und gewinnt davon 1,4,5 (3x) -> 75 %
    assert home_team.rallies_served == 4
    assert home_team.points_won_serving == 3
    assert home_team.break_rate == 75.0
    # home nimmt nur in Rally 3 an und gewinnt sie -> 100 %
    assert home_team.rallies_received == 1
    assert home_team.points_won_receiving == 1
    assert home_team.side_out_rate == 100.0

    # Punktquellen: Ass (Rally 1) + Angriffspunkt (Rally 3) + Blockpunkt (Rally 5) = 3,
    # Rest (Rally 4, Annahmefehler Gegner) fällt als Residual auf opponent_errors.
    assert home_team.point_sources.serve == 1
    assert home_team.point_sources.attack == 1
    assert home_team.point_sources.block == 1
    assert home_team.point_sources.opponent_errors == 1
    assert home_team.points_total == 4

    # away gewinnt nur Rally 2 (Aufschlagfehler von home) beim Annehmen -> 25 %
    assert away_team.rallies_received == 4
    assert away_team.points_won_receiving == 1
    assert away_team.side_out_rate == 25.0
    assert away_team.rallies_served == 1
    assert away_team.points_won_serving == 0
    assert away_team.break_rate == 0.0
    assert away_team.point_sources.serve == 0
    assert away_team.point_sources.attack == 0
    assert away_team.point_sources.block == 0
    assert away_team.point_sources.opponent_errors == 1


def test_rotation_analysis_groups_by_setter_position() -> None:
    stats = compute_match_statistics(RALLIES)
    home_rotations = {r.position: r for r in stats.rotations["home"]}
    away_rotations = {r.position: r for r in stats.rotations["away"]}

    assert set(home_rotations) == {1, 2}
    assert home_rotations[1].rallies_served == 2
    assert home_rotations[1].points_won_serving == 1
    assert home_rotations[1].rallies_received == 1
    assert home_rotations[1].points_won_receiving == 1
    assert home_rotations[2].rallies_served == 2
    assert home_rotations[2].points_won_serving == 2
    assert home_rotations[2].rallies_received == 0

    assert set(away_rotations) == {1, 2}
    assert away_rotations[1].rallies_received == 2
    assert away_rotations[1].points_won_receiving == 1
    assert away_rotations[2].rallies_served == 1
    assert away_rotations[2].rallies_received == 2
    assert away_rotations[2].points_won_receiving == 0


def test_statistics_endpoint_after_import(client: TestClient) -> None:
    imported = client.post(
        "/api/imports/dvw",
        files={"file": ("test.dvw", DVW_SAMPLE.encode("cp1252"), "text/plain")},
    ).json()

    response = client.get(f"/api/matches/{imported['match_id']}/statistics")
    assert response.status_code == 200, response.text
    body = response.json()

    assert {p["player_number"] for p in body["home_players"]} == {7}
    assert body["home_players"][0]["serve"] == {"total": 2, "errors": 1, "aces": 0}
    assert {p["player_number"] for p in body["away_players"]} == {3, 5}

    # home serviert beide Ballwechsel (kein Side-Out zugunsten away im Sample) und
    # gewinnt den ersten per gegnerischem Angriffsfehler (Rally 1: home S+, away A=).
    assert body["home_team"]["rallies_served"] == 2
    assert body["home_team"]["points_won_serving"] == 1
    assert body["home_team"]["break_rate"] == 50.0
    assert body["home_team"]["rallies_received"] == 0
    assert body["home_team"]["side_out_rate"] is None
    assert body["home_team"]["point_sources"]["opponent_errors"] == 1

    assert body["home_rotations"] == [
        {
            "position": 1,
            "rallies_served": 2,
            "points_won_serving": 1,
            "rallies_received": 0,
            "points_won_receiving": 0,
            "break_rate": 50.0,
            "side_out_rate": None,
        }
    ]


def test_statistics_endpoint_missing_match_returns_404(client: TestClient) -> None:
    response = client.get("/api/matches/999999/statistics")
    assert response.status_code == 404
