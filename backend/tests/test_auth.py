from fastapi.testclient import TestClient

from app.core.security import (
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)


def test_password_hash_roundtrip() -> None:
    stored = hash_password("s3cret!")
    assert verify_password("s3cret!", stored)
    assert not verify_password("falsch", stored)
    assert not verify_password("s3cret!", "kaputt")


def test_session_token_roundtrip_and_tampering() -> None:
    token = create_session_token(42, "key", ttl_seconds=60)
    assert verify_session_token(token, "key") == 42
    assert verify_session_token(token, "anderer-key") is None
    assert verify_session_token(token + "x", "key") is None
    expired = create_session_token(42, "key", ttl_seconds=-1)
    assert verify_session_token(expired, "key") is None


def test_api_requires_login(anon_client: TestClient) -> None:
    assert anon_client.get("/api/teams").status_code == 401
    assert anon_client.get("/api/matches").status_code == 401
    assert anon_client.get("/api/auth/me").status_code == 401
    assert anon_client.get("/health").status_code == 200  # Healthcheck bleibt offen


def test_login_logout_flow(anon_client: TestClient, db_session) -> None:
    from app.models import User

    db_session.add(User(username="alice", password_hash=hash_password("pw")))
    db_session.commit()

    assert (
        anon_client.post(
            "/api/auth/login", json={"username": "alice", "password": "falsch"}
        ).status_code
        == 401
    )
    response = anon_client.post("/api/auth/login", json={"username": "alice", "password": "pw"})
    assert response.status_code == 200
    assert response.json() == {"username": "alice", "role": "admin"}

    assert anon_client.get("/api/auth/me").json()["username"] == "alice"
    assert anon_client.get("/api/teams").status_code == 200

    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/teams").status_code == 401


def test_viewer_is_read_only(viewer_client: TestClient) -> None:
    assert viewer_client.get("/api/teams").status_code == 200
    response = viewer_client.post("/api/teams", json={"code": "X", "name": "Verboten"})
    assert response.status_code == 403
    assert viewer_client.get("/api/auth/me").json()["role"] == "viewer"


def test_viewer_cannot_edit_teams_or_players(viewer_client: TestClient) -> None:
    assert viewer_client.patch("/api/teams/1", json={"code": "X", "name": "Verboten"}).status_code == 403
    assert (
        viewer_client.patch(
            "/api/teams/1/players/1", json={"number": 1, "last_name": "Verboten"}
        ).status_code
        == 403
    )
