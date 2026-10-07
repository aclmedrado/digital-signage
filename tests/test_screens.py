from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.main import app

DATA = {"name": "TV Recepção", "slug": "recepcao", "location": "Recepção"}


def create(client, **changes):
    return client.post("/api/screens", json={**DATA, **changes})


def test_create(client):
    response = create(client)
    assert response.status_code == 201
    data = response.json()
    assert {key: data[key] for key in DATA} == DATA
    assert data["active"] is True
    assert isinstance(data["id"], int)
    assert datetime.fromisoformat(data["created_at"]).utcoffset().total_seconds() == 0
    assert datetime.fromisoformat(data["updated_at"]).utcoffset().total_seconds() == 0


def test_list(client):
    assert client.get("/api/screens").json() == []
    first = create(client).json()
    second = create(client, slug="tv-02").json()
    response = client.get("/api/screens")
    assert response.status_code == 200
    assert response.json() == [first, second]


def test_read(client):
    data = create(client).json()
    response = client.get(f"/api/screens/{data['id']}")
    assert response.status_code == 200
    assert response.json() == data


def test_missing(client):
    assert client.get("/api/screens/999").status_code == 404
    assert client.patch("/api/screens/999", json={"name": "Outra"}).status_code == 404


def test_patch(client):
    data = create(client).json()
    response = client.patch(f"/api/screens/{data['id']}", json={"name": "TV Nova"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "TV Nova"
    for field in ("id", "slug", "location", "active", "created_at"):
        assert updated[field] == data[field]
    assert updated["updated_at"] > data["updated_at"]


def test_deactivate_and_activate(client):
    data = create(client).json()
    url = f"/api/screens/{data['id']}"
    assert client.patch(url, json={"active": False}).json()["active"] is False
    assert client.get(url).json()["active"] is False
    assert client.patch(url, json={"active": True}).json()["active"] is True


def test_duplicate(client, isolated_database):
    first = create(client).json()
    assert create(client).status_code == 409
    second = create(client, slug="tv-02").json()
    url = f"/api/screens/{second['id']}"
    response = client.patch(url, json={"slug": first["slug"]})
    assert response.status_code == 409
    assert response.json() == {"detail": "Slug já cadastrado"}
    assert client.get(url).json()["slug"] == "tv-02"
    assert any(item["column_names"] == ["slug"] for item in inspect(isolated_database).get_unique_constraints("screens"))


@pytest.mark.parametrize("slug", ["TV Recepção", "recepção", "tv_01", "tv 01", "-recepcao", "recepcao-"])
def test_invalid_slug(client, slug):
    assert create(client, slug=slug).status_code == 422
    screen = create(client).json()
    assert client.patch(f"/api/screens/{screen['id']}", json={"slug": slug}).status_code == 422


def test_persistence_across_startup(isolated_database):
    with TestClient(app) as client:
        data = create(client).json()
    isolated_database.dispose()
    with TestClient(app) as client:
        response = client.get(f"/api/screens/{data['id']}")
        assert response.status_code == 200
        assert response.json() == data


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_server_fields_cannot_be_changed(client, field):
    data = create(client).json()
    assert client.patch(f"/api/screens/{data['id']}", json={field: data[field]}).status_code == 422


@pytest.mark.parametrize("field", ["name", "slug", "location", "active"])
def test_patch_rejects_null(client, field):
    data = create(client).json()
    assert client.patch(f"/api/screens/{data['id']}", json={field: None}).status_code == 422
