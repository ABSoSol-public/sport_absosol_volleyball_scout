from fastapi.testclient import TestClient

HOME_LINEUP = [1, 2, 3, 4, 5, 6]
AWAY_LINEUP = [11, 12, 13, 14, 15, 16]


def _create_match(client: TestClient) -> int:
    home = client.post("/api/teams", json={"code": "HEI", "name": "Heimteam"}).json()
    away = client.post("/api/teams", json={"code": "GAS", "name": "Gastteam"}).json()
    response = client.post(
        "/api/matches",
        json={
            "match_date": "2026-07-27",
            "competition": "Testliga",
            "home_team_id": home["id"],
            "away_team_id": away["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_team_and_player_creation(client: TestClient) -> None:
    team = client.post("/api/teams", json={"code": "TST", "name": "Testteam"})
    assert team.status_code == 201
    team_id = team.json()["id"]

    player = client.post(
        f"/api/teams/{team_id}/players", json={"number": 7, "last_name": "Musterfrau"}
    )
    assert player.status_code == 201

    duplicate = client.post(
        f"/api/teams/{team_id}/players", json={"number": 7, "last_name": "Doppelt"}
    )
    assert duplicate.status_code == 409

    detail = client.get(f"/api/teams/{team_id}")
    assert detail.status_code == 200
    assert len(detail.json()["players"]) == 1


def test_live_scouting_flow(client: TestClient) -> None:
    match_id = _create_match(client)

    response = client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    assert response.status_code == 200, response.text

    # Rally mit Scout-Codes: Aufschlag Heim 5, Annahme Gast 11, Angriff Gast 14 → Punkt Gast
    response = client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "away", "actions": ["5SQ-", "a11RQ+", "a14AH#"]},
    )
    assert response.status_code == 200, response.text
    state = response.json()
    assert state["current_set"]["points"] == {"home": 0, "away": 1}
    assert state["current_set"]["serving"] == "away"
    assert state["current_set"]["lineups"]["away"] == [12, 13, 14, 15, 16, 11]

    # Ungültiger Scout-Code wird abgelehnt und ändert nichts
    response = client.post(
        f"/api/matches/{match_id}/live/rally", json={"winner": "home", "actions": ["9XY"]}
    )
    assert response.status_code == 422

    # Wechsel + Auszeit
    assert (
        client.post(
            f"/api/matches/{match_id}/live/substitution",
            json={"side": "home", "player_out": 1, "player_in": 9},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/matches/{match_id}/live/timeout", json={"side": "home"}).status_code
        == 200
    )

    # Undo: Auszeit zurücknehmen
    response = client.post(f"/api/matches/{match_id}/live/undo")
    assert response.status_code == 200
    assert response.json()["current_set"]["timeouts"] == {"home": 0, "away": 0}

    # Zustand ist aus Events reproduzierbar
    state = client.get(f"/api/matches/{match_id}/live/state").json()
    assert state["current_set"]["points"] == {"home": 0, "away": 1}
    assert 9 in state["current_set"]["lineups"]["home"]

    match = client.get(f"/api/matches/{match_id}").json()
    assert match["status"] == "live"


def test_rule_violation_returns_422(client: TestClient) -> None:
    match_id = _create_match(client)
    response = client.post(
        f"/api/matches/{match_id}/live/rally", json={"winner": "home", "actions": []}
    )
    assert response.status_code == 422  # kein Satz gestartet
