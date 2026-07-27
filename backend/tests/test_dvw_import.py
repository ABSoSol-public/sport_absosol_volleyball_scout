from fastapi.testclient import TestClient

from app.dvw import parse_dvw

# Synthetische Minimal-Datei nach docs/DVW-FORMAT.md (anonymisierte Struktur,
# angelehnt an reale Beispiele — keine echten Personen).
DVW_SAMPLE = "\r\n".join(
    [
        "[3DATAVOLLEYSCOUT]",
        "FILEFORMAT: 2.0",
        "GENERATOR-PRG: Data Volley",
        "[3MATCH]",
        "17/10/2010;19.30.00;2010/2011;Testliga;Vorrunde;;So;;1;1;Z;0;",
        ";;40468;",
        "[3TEAMS]",
        "TSA;Team Alpha;1;Trainer A;;16777215;",
        "TSB;Team Beta;0;Trainer B;;255;",
        "[3MORE]",
        ";;;;;Scout Test;",
        "[3COMMENTS]",
        "no comments",
        "[3SET]",
        "True;8 -6;16-14;21-19;25-20;24;",
        "True;;;;;;",
        "True;;;;;;",
        "True;;;;;;",
        "True;;;;;;",
        "[3PLAYERS-H]",
        "0;7;1;1;;;;;ALPEIN;Alpha-Eins;Anna;;;2;False;;;",
        "0;9;2;2;;;;;ALPZWE;Alpha-Zwei;Berta;;L;6;False;;;",
        "[3PLAYERS-V]",
        "1;3;1;1;;;;;BETEIN;Beta-Eins;Carla;;;2;False;;;",
        "1;5;2;2;;;;;BETZWE;Beta-Zwei;Doris;;;3;False;;;",
        "[3ATTACKCOMBINATION]",
        "[3SETTERCALL]",
        "[3WINNINGSYMBOLS]",
        "[3RESERVE]",
        "[3SCOUT]",
        "*P07>LUp;;;;;;;;1;1;1;;;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "*z1>LUp;;;;;;;;1;1;1;;;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "*07SQ+~~~15;;;;;;19.31.21;1;1;1;1;100;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "a03RQ-~~~15;;;;;;19.31.21;1;1;1;1;100;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "a05AH=~~~24~H;;s;;;;19.31.27;1;1;1;1;105;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "*p01:00;;;;;;19.31.30;1;1;1;1;108;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "*07SQ=;;;;;;19.31.50;1;1;1;1;120;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "ap01:01;;;;;;19.31.52;1;1;1;1;122;;7;9;0;0;0;0;3;5;0;0;0;0;",
        "**1set;;;;;;19.55.00;1;1;1;1;500;;7;9;0;0;0;0;3;5;0;0;0;0;",
    ]
)


def test_parse_dvw_sample() -> None:
    parsed = parse_dvw(DVW_SAMPLE.encode("cp1252"))
    assert parsed.match_date is not None and parsed.match_date.year == 2010
    assert parsed.competition == "Testliga"
    assert parsed.home_team.code == "TSA" and parsed.away_team.name == "Team Beta"
    assert [p.number for p in parsed.home_players] == [7, 9]
    assert parsed.home_players[1].is_libero
    assert parsed.sets[0].final_score == (25, 20)
    assert parsed.sets[0].duration_minutes == 24

    # LUp-Zeilen werden übersprungen; 5 Aktions-/Punkt-/Satzende-Codes bleiben
    skills = [r.skill for r in parsed.scout_rows if r.skill]
    assert skills == ["S", "R", "A", "S"]
    attack = next(r for r in parsed.scout_rows if r.skill == "A")
    assert attack.side == "away" and attack.player_number == 5
    assert attack.evaluation == "=" and attack.start_zone == 2 and attack.end_zone == 4
    point = next(r for r in parsed.scout_rows if r.point_side)
    assert point.point_side == "home" and (point.home_score, point.away_score) == (1, 0)


def test_import_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/imports/dvw",
        files={"file": ("test.dvw", DVW_SAMPLE.encode("cp1252"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["teams_created"] == 2
    assert body["players_created"] == 4
    assert body["sets"] == 1
    assert body["rallies"] == 2
    assert body["actions"] == 4

    match = client.get(f"/api/matches/{body['match_id']}").json()
    assert match["home_team"]["name"] == "Team Alpha"
    assert match["status"] == "finished"

    # Re-Import: Teams/Spieler werden wiederverwendet, neues Match entsteht
    again = client.post(
        "/api/imports/dvw",
        files={"file": ("test.dvw", DVW_SAMPLE.encode("cp1252"), "text/plain")},
    ).json()
    assert again["teams_created"] == 0
    assert again["players_created"] == 0


def test_import_rejects_invalid_file(client: TestClient) -> None:
    response = client.post(
        "/api/imports/dvw", files={"file": ("kaputt.dvw", b"kein dvw", "text/plain")}
    )
    assert response.status_code == 422


def test_import_forbidden_for_viewer(viewer_client: TestClient) -> None:
    response = viewer_client.post(
        "/api/imports/dvw",
        files={"file": ("test.dvw", DVW_SAMPLE.encode("cp1252"), "text/plain")},
    )
    assert response.status_code == 403
