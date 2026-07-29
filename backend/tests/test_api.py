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
    assert player.json()["position"] == ""
    assert player.json()["is_youth_player"] is False

    duplicate = client.post(
        f"/api/teams/{team_id}/players", json={"number": 7, "last_name": "Doppelt"}
    )
    assert duplicate.status_code == 409

    detail = client.get(f"/api/teams/{team_id}")
    assert detail.status_code == 200
    assert len(detail.json()["players"]) == 1


def test_player_rejects_unknown_position(client: TestClient) -> None:
    team_id = client.post("/api/teams", json={"code": "POS", "name": "Positionsteam"}).json()["id"]
    response = client.post(
        f"/api/teams/{team_id}/players",
        json={"number": 1, "last_name": "Test", "position": "Torwart"},
    )
    assert response.status_code == 422


def test_team_update(client: TestClient) -> None:
    ids = [
        client.post("/api/teams", json={"code": c, "name": n}).json()["id"]
        for c, n in [("UPA", "Alt A"), ("UPB", "Alt B")]
    ]

    response = client.patch(f"/api/teams/{ids[0]}", json={"code": "UPA", "name": "Neuer Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "Neuer Name"

    conflict = client.patch(f"/api/teams/{ids[0]}", json={"code": "UPB", "name": "Neuer Name"})
    assert conflict.status_code == 409

    assert client.patch("/api/teams/999999", json={"code": "XXX", "name": "?"}).status_code == 404


def test_player_update(client: TestClient) -> None:
    team_id = client.post("/api/teams", json={"code": "UPP", "name": "Update-Team"}).json()["id"]
    player = client.post(
        f"/api/teams/{team_id}/players",
        json={"number": 4, "last_name": "Vorher", "position": "Außenangreifer"},
    ).json()
    other = client.post(
        f"/api/teams/{team_id}/players", json={"number": 9, "last_name": "Andere"}
    ).json()

    response = client.patch(
        f"/api/teams/{team_id}/players/{player['id']}",
        json={
            "number": 4,
            "last_name": "Nachher",
            "position": "Mittelblocker",
            "is_youth_player": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["last_name"] == "Nachher"
    assert body["position"] == "Mittelblocker"
    assert body["is_youth_player"] is True

    conflict = client.patch(
        f"/api/teams/{team_id}/players/{player['id']}",
        json={"number": other["number"], "last_name": "X"},
    )
    assert conflict.status_code == 409

    assert (
        client.patch(
            f"/api/teams/{team_id}/players/999999", json={"number": 1, "last_name": "?"}
        ).status_code
        == 404
    )


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


def test_match_sets_empty_for_live_scouted_match(client: TestClient) -> None:
    # Vor Roadmap 2.6 (Zusammenführung Analyse-/Live-Strang) füllt Live-Scouting
    # nur `live_events`, nicht `match_sets` — der Sets-Endpunkt liefert dafür
    # bewusst eine leere Liste statt eines Fehlers.
    match_id = _create_match(client)
    assert client.get(f"/api/matches/{match_id}/sets").json() == []


def test_match_sets_missing_match_returns_404(client: TestClient) -> None:
    assert client.get("/api/matches/999999/sets").status_code == 404
