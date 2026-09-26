"""Libero-Wechsel als eigener Live-Endpunkt (`POST .../live/libero-replacement`):
unbegrenzt, zählt nicht gegen das Wechsellimit, aber die API-Schicht prüft
zusätzlich, dass `player_in` im Kader tatsächlich als Libero markiert ist
(die Engine selbst kennt keine Spielerrollen, siehe app/api/live.py).
"""

from fastapi.testclient import TestClient

HOME_LINEUP = [1, 2, 3, 4, 5, 6]
AWAY_LINEUP = [11, 12, 13, 14, 15, 16]


def _create_match_with_libero(client: TestClient) -> int:
    home = client.post("/api/teams", json={"code": "HEI", "name": "Heimteam"}).json()
    away = client.post("/api/teams", json={"code": "GAS", "name": "Gastteam"}).json()
    for number in HOME_LINEUP:
        client.post(f"/api/teams/{home['id']}/players", json={"number": number, "last_name": f"H{number}"})
    client.post(
        f"/api/teams/{home['id']}/players",
        json={"number": 20, "last_name": "Libero", "is_libero": True},
    )
    for number in AWAY_LINEUP:
        client.post(f"/api/teams/{away['id']}/players", json={"number": number, "last_name": f"G{number}"})
    match_id = client.post(
        "/api/matches",
        json={
            "match_date": "2026-09-26",
            "home_team_id": home["id"],
            "away_team_id": away["id"],
            "substitutions_per_set": 0,  # regulärer Wechsel darf hier gar nicht mehr
        },
    ).json()["id"]
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    return match_id


def test_libero_replacement_bypasses_substitution_limit(client: TestClient) -> None:
    match_id = _create_match_with_libero(client)

    response = client.post(
        f"/api/matches/{match_id}/live/libero-replacement",
        json={"side": "home", "player_out": 6, "player_in": 20},
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_set"]["lineups"]["home"] == [1, 2, 3, 4, 5, 20]
    assert response.json()["current_set"]["substitutions"]["home"] == 0
    assert response.json()["current_set"]["libero_replacements"]["home"] == 1

    back = client.post(
        f"/api/matches/{match_id}/live/libero-replacement",
        json={"side": "home", "player_out": 20, "player_in": 6},
    )
    assert back.status_code == 200, back.text
    assert back.json()["current_set"]["libero_replacements"]["home"] == 2


def test_libero_replacement_rejects_non_libero_player(client: TestClient) -> None:
    match_id = _create_match_with_libero(client)
    response = client.post(
        f"/api/matches/{match_id}/live/libero-replacement",
        json={"side": "home", "player_out": 6, "player_in": 2},  # 2 ist kein Libero
    )
    assert response.status_code == 422
    assert "Libero" in response.json()["detail"]


def test_libero_replacement_rejects_unknown_player_number(client: TestClient) -> None:
    match_id = _create_match_with_libero(client)
    response = client.post(
        f"/api/matches/{match_id}/live/libero-replacement",
        json={"side": "home", "player_out": 6, "player_in": 77},
    )
    assert response.status_code == 422


def test_regular_substitution_endpoint_still_enforces_the_limit(client: TestClient) -> None:
    match_id = _create_match_with_libero(client)
    response = client.post(
        f"/api/matches/{match_id}/live/substitution",
        json={"side": "home", "player_out": 6, "player_in": 20},
    )
    assert response.status_code == 422  # substitutions_per_set=0
