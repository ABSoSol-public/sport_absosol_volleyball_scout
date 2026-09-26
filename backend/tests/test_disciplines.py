"""Mehrfach-Formate (Halle 6:6/4:4/3:3/2:2, Beach 2:2) und Zuspielsystem.

Die Engine (`Rules`/`MatchEngine`) war für beliebige `players_on_court` schon
immer generisch — dieser Test deckt ab, dass `Match.discipline` das Preset
tatsächlich bis in die Engine durchreicht (vorher gab es dafür gar keine
Spalte, `Rules.players_on_court` blieb beim Default 6), inklusive Override
einzelner Regelfelder und der abgeleiteten Analyse-/Export-Stränge.
"""

from fastapi.testclient import TestClient


def _create_teams(client: TestClient) -> tuple[int, int]:
    home = client.post("/api/teams", json={"code": "HEI", "name": "Heimteam"}).json()
    away = client.post("/api/teams", json={"code": "GAS", "name": "Gastteam"}).json()
    for number in (1, 2):
        client.post(f"/api/teams/{home['id']}/players", json={"number": number, "last_name": f"H{number}"})
        client.post(f"/api/teams/{away['id']}/players", json={"number": number + 10, "last_name": f"G{number}"})
    return home["id"], away["id"]


def test_list_disciplines_returns_all_presets(client: TestClient) -> None:
    response = client.get("/api/disciplines")
    assert response.status_code == 200, response.text
    codes = {p["code"] for p in response.json()}
    assert codes == {"hall_6", "hall_4", "hall_3", "hall_2", "beach_2"}
    beach = next(p for p in response.json() if p["code"] == "beach_2")
    assert beach["players_on_court"] == 2
    assert beach["points_per_set"] == 21
    assert beach["substitutions_per_set"] == 0
    assert beach["has_libero"] is False


def test_match_create_applies_discipline_preset(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    response = client.post(
        "/api/matches",
        json={
            "match_date": "2026-09-26",
            "home_team_id": home_id,
            "away_team_id": away_id,
            "discipline": "beach_2",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["discipline"] == "beach_2"
    assert body["players_on_court"] == 2
    assert body["points_per_set"] == 21
    assert body["substitutions_per_set"] == 0


def test_match_create_can_override_single_preset_field(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    response = client.post(
        "/api/matches",
        json={
            "match_date": "2026-09-26",
            "home_team_id": home_id,
            "away_team_id": away_id,
            "discipline": "beach_2",
            "points_per_set": 15,
        },
    )
    body = response.json()
    assert body["points_per_set"] == 15  # Override
    assert body["players_on_court"] == 2  # weiterhin aus dem Preset


def test_two_player_discipline_plays_end_to_end(client: TestClient) -> None:
    home_id, away_id = _create_teams(client)
    match_id = client.post(
        "/api/matches",
        json={
            "match_date": "2026-09-26",
            "home_team_id": home_id,
            "away_team_id": away_id,
            "discipline": "beach_2",
            "best_of": 1,
            "points_per_set": 3,
            "tiebreak_points": 3,
        },
    ).json()["id"]

    start = client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": [1, 2], "away_lineup": [11, 12]},
    )
    assert start.status_code == 200, start.text

    # Ein Wechsel muss bei Beach abgelehnt werden (Preset substitutions_per_set=0).
    sub = client.post(
        f"/api/matches/{match_id}/live/substitution",
        json={"side": "home", "player_out": 1, "player_in": 2},
    )
    assert sub.status_code == 422

    for _ in range(3):
        client.post(f"/api/matches/{match_id}/live/rally", json={"winner": "home", "actions": ["1SQ#"]})

    match = client.get(f"/api/matches/{match_id}").json()
    assert match["status"] == "finished"
    sets = client.get(f"/api/matches/{match_id}/sets").json()
    assert sets[0]["home_points"] == 3 and sets[0]["away_points"] == 0

    export = client.get(f"/api/matches/{match_id}/export")
    assert export.status_code == 200, export.text


def test_team_setter_system_roundtrip(client: TestClient) -> None:
    created = client.post(
        "/api/teams", json={"code": "SET", "name": "Setter-Team", "setter_system": "4-2"}
    )
    assert created.status_code == 201, created.text
    assert created.json()["setter_system"] == "4-2"

    team_id = created.json()["id"]
    updated = client.patch(
        f"/api/teams/{team_id}",
        json={"code": "SET", "name": "Setter-Team", "setter_system": "5-1"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["setter_system"] == "5-1"

    cleared = client.patch(
        f"/api/teams/{team_id}",
        json={"code": "SET", "name": "Setter-Team", "setter_system": None},
    )
    assert cleared.json()["setter_system"] is None


def test_team_setter_system_rejects_unknown_value(client: TestClient) -> None:
    response = client.post(
        "/api/teams", json={"code": "BAD", "name": "Ungueltig", "setter_system": "7-0"}
    )
    assert response.status_code == 422
