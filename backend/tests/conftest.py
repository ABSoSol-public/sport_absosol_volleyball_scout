from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Client ohne Login — für Auth-Tests."""
    yield from _make_client(db_session)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Client mit eingeloggtem Admin (Standard für Fach-Tests)."""
    db_session.add(User(username="test-admin", password_hash=hash_password("geheim")))
    db_session.commit()
    for test_client in _make_client(db_session):
        response = test_client.post(
            "/api/auth/login", json={"username": "test-admin", "password": "geheim"}
        )
        assert response.status_code == 200, response.text
        yield test_client


@pytest.fixture()
def viewer_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Client mit eingeloggtem Nur-Lese-Nutzer."""
    db_session.add(
        User(username="test-viewer", password_hash=hash_password("geheim"), role="viewer")
    )
    db_session.commit()
    for test_client in _make_client(db_session):
        response = test_client.post(
            "/api/auth/login", json={"username": "test-viewer", "password": "geheim"}
        )
        assert response.status_code == 200, response.text
        yield test_client
