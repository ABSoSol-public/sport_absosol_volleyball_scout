"""Spielerprofile (Karrierestatistik über mehrere Matches/Saisons) und die
FIFA-Style Skill-Karte (Perzentilrang gegen alle Spieler derselben Disziplin
in der Datenbank) — siehe app/api/players.py, docs/SPIELERPROFILE.md.
"""

from fastapi.testclient import TestClient

HOME_LINEUP = [1, 2, 3, 4, 5, 6]
AWAY_LINEUP = [11, 12, 13, 14, 15, 16]


def _create_teams(client: TestClient) -> tuple[int, int]:
    home = client.post("/api/teams", json={"code": "HEI", "name": "Heimteam"}).json()
    away = client.post("/api/teams", json={"code": "GAS", "name": "Gastteam"}).json()
    for number in HOME_LINEUP:
        client.post(f"/api/teams/{home['id']}/players", json={"number": number, "last_name": f"H{number}"})
    for number in AWAY_LINEUP:
        client.post(f"/api/teams/{away['id']}/players", json={"number": number, "last_name": f"G{number}"})
    return home["id"], away["id"]


def _create_match(client: TestClient, home_id: int, away_id: int, match_date: str) -> int:
    response = client.post(
        "/api/matches",
        json={
            "match_date": match_date,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "best_of": 1,
            "points_per_set": 25,
            "tiebreak_points": 15,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _play_rally(client: TestClient, match_id: int, winner: str, actions: list[str]) -> None:
    response = client.post(
        f"/api/matches/{match_id}/live/rally", json={"winner": winner, "actions": actions}
    )
    assert response.status_code == 200, response.text


def test_player_profile_aggregates_across_matches_and_seasons(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)

    match1 = _create_match(client, home_id, away_id, "2024-08-15")  # Saison 2024/2025
    client.post(
        f"/api/matches/{match1}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    _play_rally(client, match1, "home", ["1AH#45"])
    _play_rally(client, match1, "home", ["1AH#45"])
    _play_rally(client, match1, "away", ["1AH=46"])

    match2 = _create_match(client, home_id, away_id, "2025-09-01")  # Saison 2025/2026
    client.post(
        f"/api/matches/{match2}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    _play_rally(client, match2, "home", ["1AH#45"])

    response = client.get(f"/api/players/{home_id}/1/profile?discipline=hall_6")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["last_name"] == "H1"
    assert body["career"]["attack"] == {
        "total": 4, "errors": 1, "blocked": 0, "kills": 3,
        "efficiency": 0.5, "kill_pct": 75.0,
    }
    assert body["career"]["matches"] == 2

    seasons = {s["season"]["label"] for s in body["by_season"]}
    assert seasons == {"2024/2025", "2025/2026"}
    season_2024 = next(s for s in body["by_season"] if s["season"]["label"] == "2024/2025")
    assert season_2024["stats"]["attack"]["total"] == 3

    tendencies = body["attack_tendencies"]
    assert tendencies[0]["start_zone"] == 4 and tendencies[0]["end_zone"] == 5
    assert tendencies[0]["attempts"] == 3 and tendencies[0]["positive"] == 3
    assert tendencies[1]["start_zone"] == 4 and tendencies[1]["end_zone"] == 6
    assert tendencies[1]["errors"] == 1


def test_player_profile_season_filter_narrows_results(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    match1 = _create_match(client, home_id, away_id, "2024-08-15")
    client.post(
        f"/api/matches/{match1}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    _play_rally(client, match1, "home", ["1SQ#"])

    all_time = client.get(f"/api/players/{home_id}/1/profile?discipline=hall_6").json()
    season_id = all_time["by_season"][0]["season"]["id"]

    filtered = client.get(
        f"/api/players/{home_id}/1/profile?discipline=hall_6&season_id={season_id}"
    ).json()
    assert filtered["career"]["serve"]["total"] == 1
    assert filtered["season"]["id"] == season_id

    missing_season = client.get(f"/api/players/{home_id}/1/profile?discipline=hall_6&season_id=999999")
    assert missing_season.status_code == 404


def test_player_profile_unknown_player_returns_404(client: TestClient) -> None:
    home_id, _away_id = _create_teams(client)
    response = client.get(f"/api/players/{home_id}/99/profile")
    assert response.status_code == 404


def test_skill_card_ranks_players_by_serve_performance(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    match_id = _create_match(client, home_id, away_id, "2024-08-15")
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    # Spieler 1 (home): 6 Asse von 6 Aufschlägen -> starke Metrik.
    for _ in range(6):
        _play_rally(client, match_id, "home", ["1SQ#"])
    # Spieler 11 (away): 3 Aufschlagfehler von 6 -> schwache Metrik.
    for _ in range(3):
        _play_rally(client, match_id, "home", ["a11SQ="])
    for _ in range(3):
        _play_rally(client, match_id, "away", ["a11SQ+"])

    strong = client.get(f"/api/players/{home_id}/1/card?discipline=hall_6").json()
    weak = client.get(f"/api/players/{away_id}/11/card?discipline=hall_6").json()

    assert strong["categories"]["serve"]["sample_size"] == 6
    assert weak["categories"]["serve"]["sample_size"] == 6
    assert strong["categories"]["serve"]["rating"] > weak["categories"]["serve"]["rating"]
    assert strong["categories"]["serve"]["population_size"] == 2
    # Reception/Angriff/Block wurden nie gescoutet -> keine Bewertung statt einer 0.
    assert strong["categories"]["attack"]["rating"] is None
    assert strong["overall"] is not None


def test_skill_card_below_min_sample_has_no_rating(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    match_id = _create_match(client, home_id, away_id, "2024-08-15")
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    _play_rally(client, match_id, "home", ["1SQ#"])
    _play_rally(client, match_id, "away", ["a11RQ+"])

    card = client.get(f"/api/players/{home_id}/1/card?discipline=hall_6").json()
    assert card["categories"]["serve"]["sample_size"] == 1
    assert card["categories"]["serve"]["rating"] is None  # unter MIN_SAMPLE=6


def test_skill_card_scoped_to_discipline(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    match_id = _create_match(client, home_id, away_id, "2024-08-15")
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    for _ in range(6):
        _play_rally(client, match_id, "home", ["1SQ#"])

    beach_card = client.get(f"/api/players/{home_id}/1/card?discipline=beach_2").json()
    assert beach_card["categories"]["serve"]["population_size"] == 0
    assert beach_card["overall"] is None
