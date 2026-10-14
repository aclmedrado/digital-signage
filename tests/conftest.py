import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import MediaSettings, get_media_settings
from app.database import get_session, make_engine
from app.main import app


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
def client():
    with TestClient(app) as client:
        yield client
