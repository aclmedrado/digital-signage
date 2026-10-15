import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import MediaSettings, get_media_settings
from app.database import get_session, make_engine
from app.main import app
from tests.helpers import AuthenticatedClient


@pytest.fixture(autouse=True)
def isolated_auth_config(monkeypatch):
    # Nenhum teste herda transporte inseguro ou limites do .env de produção.
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("LOCAL_AUTH_TEST_MODE", "false")
    monkeypatch.setenv("SIGNAGE_BIND_IP", "127.0.0.1")
    monkeypatch.setenv("SIGNAGE_PORT", "8080")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "")
    for name in ("SESSION_ABSOLUTE_SECONDS", "SESSION_IDLE_SECONDS", "SESSION_TOUCH_SECONDS",
                 "LOGIN_CHALLENGE_SECONDS", "LOGIN_ATTEMPT_WINDOW_SECONDS",
                 "LOGIN_ACCOUNT_ATTEMPTS", "LOGIN_ORIGIN_ATTEMPTS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(app.state, "auth_clock", lambda: datetime(2026, 10, 14, 12, tzinfo=timezone.utc))


@pytest.fixture(autouse=True)
def isolated_media(tmp_path):
    directory = tmp_path / "media"
    directory.mkdir()
    settings = MediaSettings(directory=directory)
    app.dependency_overrides[get_media_settings] = lambda: settings
    try:
        yield settings
    finally:
        app.dependency_overrides.pop(get_media_settings, None)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    factory = sessionmaker(bind=engine)
    original_engine = app.state.engine
    app.state.engine = engine

    def test_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.state.engine = original_engine
        engine.dispose()


@pytest.fixture
def client(isolated_database):
    with AuthenticatedClient(app) as client:
        client.authenticate(isolated_database)
        yield client


@pytest.fixture
def anonymous_client():
    with TestClient(app, base_url="https://testserver") as client:
        yield client
