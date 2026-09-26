"""Roadmap 2.7: Live-gescoutete Matches bekommen automatisch einen
Analyse-Strang (`match_sets`/`rallies`/`scout_actions`), damit Statistik und
Match-Browser (`GET .../sets`, `GET .../statistics`) dieselben Daten liefern
wie bei einem DVW-Import — siehe `app/analyse_sync.py`.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MatchSet

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


def test_live_scouted_rallies_appear_in_sets_and_statistics(client: TestClient) -> None:
    match_id = _create_match(client)
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "home", "actions": ["1SQ#"]},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "away", "actions": ["2S=", "a11RQ#", "a14AH#"]},
    )

    sets = client.get(f"/api/matches/{match_id}/sets").json()
    assert len(sets) == 1
    assert sets[0]["home_points"] == 1 and sets[0]["away_points"] == 1
    assert sets[0]["finished"] is False

    stats = client.get(f"/api/matches/{match_id}/statistics").json()
    home_player_1 = next(p for p in stats["home_players"] if p["player_number"] == 1)
    assert home_player_1["serve"] == {"total": 1, "errors": 0, "aces": 1}
    away_player_14 = next(p for p in stats["away_players"] if p["player_number"] == 14)
    assert away_player_14["attack"]["total"] == 1


def test_undo_removes_derived_rally(client: TestClient) -> None:
    match_id = _create_match(client)
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "home", "actions": ["1SQ#"]},
    )
    client.post(f"/api/matches/{match_id}/live/undo")

    sets = client.get(f"/api/matches/{match_id}/sets").json()
    assert sets == [] or (sets[0]["home_points"] == 0 and sets[0]["away_points"] == 0)


def test_finished_set_and_second_set_get_separate_rally_numbering(client: TestClient) -> None:
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
    match_id = client.post(
        "/api/matches",
        json={
            "match_date": "2026-07-27",
            "home_team_id": home["id"],
            "away_team_id": away["id"],
            "best_of": 1,
            "points_per_set": 3,
            "tiebreak_points": 3,
        },
    ).json()["id"]

    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    for _ in range(3):
        client.post(f"/api/matches/{match_id}/live/rally", json={"winner": "home"})

    match = client.get(f"/api/matches/{match_id}").json()
    assert match["status"] == "finished"

    sets = client.get(f"/api/matches/{match_id}/sets").json()
    assert len(sets) == 1
    assert sets[0]["number"] == 1
    assert sets[0]["finished"] is True
    assert sets[0]["home_points"] == 3 and sets[0]["away_points"] == 0


def test_history_correction_updates_derived_statistics(client: TestClient) -> None:
    match_id = _create_match(client)
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "home", "actions": ["1SQ#"]},
    )

    history = client.get(f"/api/matches/{match_id}/live/history").json()
    rally_seq = next(row["seq"] for row in history if row["event_type"] == "rally")
    client.patch(
        f"/api/matches/{match_id}/live/history/{rally_seq}", json={"actions": ["1SQ="]}
    )

    stats = client.get(f"/api/matches/{match_id}/statistics").json()
    home_player_1 = next(p for p in stats["home_players"] if p["player_number"] == 1)
    assert home_player_1["serve"] == {"total": 1, "errors": 1, "aces": 0}


def test_backfill_syncs_pre_existing_live_events_on_read(
    client: TestClient, db_session: Session
) -> None:
    # Match, dessen live_events bereits vor Einführung von sync_from_live_events
    # aufgezeichnet wurden (Altdaten) — hier simuliert, indem die vom
    # sofortigen Sync erzeugten match_sets nachträglich wieder gelöscht
    # werden, bevor der Lesezugriff sie per Backfill neu aufbaut.
    match_id = _create_match(client)
    client.post(
        f"/api/matches/{match_id}/live/set",
        json={"serving": "home", "home_lineup": HOME_LINEUP, "away_lineup": AWAY_LINEUP},
    )
    client.post(
        f"/api/matches/{match_id}/live/rally",
        json={"winner": "home", "actions": ["1SQ#"]},
    )

    for match_set in db_session.scalars(select(MatchSet).where(MatchSet.match_id == match_id)):
        db_session.delete(match_set)
    db_session.commit()
    assert db_session.scalar(select(MatchSet).where(MatchSet.match_id == match_id)) is None

    sets = client.get(f"/api/matches/{match_id}/sets").json()
    assert len(sets) == 1
    assert sets[0]["home_points"] == 1
