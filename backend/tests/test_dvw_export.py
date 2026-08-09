from fastapi.testclient import TestClient

from app.dvw import parse_dvw
from tests.test_dvw_import import DVW_SAMPLE

HOME_LINEUP = [1, 2, 3, 4, 5, 6]
AWAY_LINEUP = [11, 12, 13, 14, 15, 16]


def _create_match(client: TestClient) -> int:
    home = client.post("/api/teams", json={"code": "HEI", "name": "Heimteam"}).json()
    away = client.post("/api/teams", json={"code": "GAS", "name": "Gastteam"}).json()
    for number in HOME_LINEUP:
        client.post(
            f"/api/teams/{home['id']}/players", json={"number": number, "last_name": f"H{number}"}
        )
    for number in AWAY_LINEUP:
        client.post(
            f"/api/teams/{away['id']}/players", json={"number": number, "last_name": f"G{number}"}
        )
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


def test_export_missing_match_returns_404(client: TestClient) -> None:
    assert client.get("/api/matches/999999/export").status_code == 404


def test_export_without_any_data_returns_422(client: TestClient) -> None:
    match_id = _create_match(client)
    response = client.get(f"/api/matches/{match_id}/export")
    assert response.status_code == 422


def test_reexport_of_imported_match_round_trips(client: TestClient) -> None:
    # Reexport: importiertes Match wieder exportieren, das Ergebnis muss vom
    # eigenen Parser wieder verstanden werden und dieselben Kerndaten liefern
    # (Nutzerwunsch 2026-08-09: "Reexport ist auch wichtig, beides").
    imported = client.post(
        "/api/imports/dvw",
        files={"file": ("test.dvw", DVW_SAMPLE.encode("cp1252"), "text/plain")},
    ).json()
    match_id = imported["match_id"]

    response = client.get(f"/api/matches/{match_id}/export")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/plain")
    assert ".dvw" in response.headers["content-disposition"]

    reparsed = parse_dvw(response.content)
    assert reparsed.home_team.code == "TSA" and reparsed.away_team.name == "Team Beta"
    assert [p.number for p in reparsed.home_players] == [7, 9]
    assert reparsed.sets[0].final_score == (25, 20)

    skills = [r.skill for r in reparsed.scout_rows if r.skill]
    assert skills == ["S", "R", "A", "S"]
    attack = next(r for r in reparsed.scout_rows if r.skill == "A")
    assert attack.side == "away" and attack.player_number == 5
    assert attack.evaluation == "="
    assert attack.timestamp is not None

    points = [r for r in reparsed.scout_rows if r.point_side]
    assert [(p.point_side, p.home_score, p.away_score) for p in points] == [
        ("home", 1, 0),
        ("away", 1, 1),
    ]


def test_export_live_scouted_match(client: TestClient) -> None:
    match_id = _create_match(client)
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "away", "actions": ["5SQ-", "a11RQ+", "a14AH#"]},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "home", "actions": ["*3S14.11#"]},
    )

    response = client.get(f"/api/matches/{match_id}/export")
    assert response.status_code == 200, response.text

    reparsed = parse_dvw(response.content)
    assert reparsed.home_team.code == "HEI"
    assert [p.number for p in reparsed.home_players] == HOME_LINEUP
    assert [p.number for p in reparsed.away_players] == AWAY_LINEUP

    points = [r for r in reparsed.scout_rows if r.point_side]
    assert [(p.point_side, p.home_score, p.away_score) for p in points] == [
        ("away", 0, 1),
        ("home", 1, 1),
    ]

    # Erste Rallye: 3 Einzelcodes (S,R,A); zweite Rallye: Compound-Code
    # (Aufschlag+Annahme) -> wird beim Export in zwei eigenständige, gültige
    # DVW-Zeilen aufgelöst (S + R), keine unparsebare Compound-Notation.
    action_rows = [r for r in reparsed.scout_rows if r.skill]
    assert [r.skill for r in action_rows] == ["S", "R", "A", "S", "R"]

    # Einstellige Spielernummer (Heim-Spieler 5, kein Präfix im Original)
    # muss beim Export nullgepolstert und präfixiert werden, sonst verwirft
    # sie die strikte DVW-Grammatik (\\d{2}) beim Reimport stillschweigend.
    serve1 = action_rows[0]
    assert serve1.side == "home" and serve1.player_number == 5 and serve1.evaluation == "-"

    reception1 = action_rows[1]
    assert reception1.side == "away" and reception1.player_number == 11
    assert reception1.evaluation == "+"

    # Compound-Code-Hälften: Aufschlag (Heim, Spieler 3, Zone 1->4, Wertung
    # aus der Annahme "#" abgeleitet: "-") + Annahme (Gast, Spieler 11, "#").
    compound_serve, compound_reception = action_rows[3], action_rows[4]
    assert compound_serve.side == "home" and compound_serve.player_number == 3
    assert compound_serve.evaluation == "-"
    assert compound_serve.start_zone == 1 and compound_serve.end_zone == 4
    assert compound_reception.side == "away" and compound_reception.player_number == 11
    assert compound_reception.evaluation == "#"


def test_export_does_not_require_writer_role(viewer_client: TestClient) -> None:
    # Export ist ein Lesevorgang, auch fuer nur-lesende Nutzer erlaubt -- der
    # Endpunkt darf hier nicht 403 liefern (404, da kein Match existiert, ist
    # das erwartete Ergebnis).
    response = viewer_client.get("/api/matches/999999/export")
    assert response.status_code == 404
