"""Playlists: banco/mídias isolados, login real e CSRF da ETAPA 006."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from threading import Barrier
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app
from app.models import AuthSession, MediaAsset, Playlist, PlaylistItem, ScreenPlaylistAssignment, User
from app.services import playlists
from tests.test_media import image_bytes

MISSING = object()
GET_PATHS = ["/admin/playlists", "/admin/playlists/new", "/admin/playlists/1",
             "/admin/playlists/1/edit", "/admin/screens/1/playlist"]
POST_PATHS = ["/admin/playlists", "/admin/playlists/1/edit", "/admin/playlists/1/toggle",
              "/admin/playlists/1/items", "/admin/playlists/1/items/1/remove",
              "/admin/playlists/1/items/1/move-up", "/admin/playlists/1/items/1/move-down",
              "/admin/screens/1/playlist", "/admin/screens/1/playlist/unassign"]


def snapshot(engine):
    with engine.connect() as connection:
        return {table.name: connection.execute(table.select().order_by(*table.primary_key)).all()
                for table in Base.metadata.sorted_tables}


def rows(engine, model):
    with engine.connect() as connection:
        return connection.execute(model.__table__.select().order_by(*model.__table__.primary_key)).mappings().all()


def ordered(engine, playlist_id):
    return sorted((row for row in rows(engine, PlaylistItem) if row["playlist_id"] == playlist_id),
                  key=lambda row: (row["position"], row["id"]))


def assert_order(engine, playlist_id, expected):
    items = ordered(engine, playlist_id)
    assert [item["id"] for item in items] == expected
    assert [item["position"] for item in items] == list(range(1, len(items) + 1))


def html(response, code=200):
    assert response.status_code == code, response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "Traceback" not in response.text


def redirected(response, path=None):
    assert response.status_code == 303, response.text
    if path is not None:
        assert urlsplit(response.headers["location"]).path == path


def create(client, name="Playlist Piloto 007", description="Campanha"):
    response = client.post("/admin/playlists", data={"name": name, "description": description}, follow_redirects=False)
    redirected(response)
    return int(urlsplit(response.headers["location"]).path.rsplit("/", 1)[1])


def add(client, playlist_id, media_id, duration=MISSING):
    data = {"media_id": str(media_id)}
    if duration is not MISSING:
        data["duration_seconds"] = duration
    return client.post(f"/admin/playlists/{playlist_id}/items", data=data, follow_redirects=False)


@pytest.fixture
def assets(client, isolated_database, isolated_media):
    # Regras de playlists só referenciam metadados; upload/ffprobe de MP4 real
    # permanece na suíte anterior. Este vídeo não é usado como prova de reprodução.
    result = {}
    with Session(isolated_database) as session:
        for kind in ("image", "video"):
            filename = f"{uuid4()}.{'png' if kind == 'image' else 'mp4'}"
            payload = image_bytes() if kind == "image" else b"isolated-reference-to-validated-mp4" * 8
            (isolated_media.directory / filename).write_bytes(payload)
            asset = MediaAsset(title=f"Campanha {kind}", kind=kind, original_filename=filename,
                               stored_filename=filename, mime_type="image/png" if kind == "image" else "video/mp4",
                               size_bytes=len(payload), width=16, height=12,
                               frame_count=1 if kind == "image" else None,
                               duration_seconds=1.25 if kind == "video" else None,
                               video_codec="h264" if kind == "video" else None,
                               frame_rate=24 if kind == "video" else None)
            session.add(asset)
            session.flush()
            result[kind] = asset.id
        session.commit()
    return result


@pytest.fixture
def screens(client):
    result = []
    for slug, name in (("tv-piloto", "TV Piloto"), ("tv-patio", "TV do Pátio")):
        response = client.post("/api/screens", json={"name": name, "slug": slug, "location": "Teste"})
        assert response.status_code == 201
        result.append(response.json()["id"])
    return result


def test_empty_catalog_and_navigation(client):
    response = client.get("/admin/playlists")
    html(response)
    assert "Nenhuma playlist cadastrada" in response.text
    assert "/admin/playlists/new" in response.text
    for path in ("/admin/screens", "/admin/media", "/admin/playlists/new"):
        page = client.get(path)
        assert "/admin/playlists" in page.text
        assert 'name="csrf_token"' in page.text


def test_create_defaults_normalization_duplicate_names_and_utc(client, isolated_database):
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    first = create(client, "  Mesmo nome  ", "  Descrição  ")
    second = create(client, "Mesmo nome", "")
    stored = rows(isolated_database, Playlist)
    assert [row["id"] for row in stored] == [first, second]
    assert [row["name"] for row in stored] == ["Mesmo nome", "Mesmo nome"]
    assert stored[0]["description"] == "Descrição" and stored[1]["description"] is None
    assert all(row["active"] for row in stored)
    assert all(before <= row["created_at"] <= datetime.now(timezone.utc).replace(tzinfo=None) for row in stored)
    assert all(row["updated_at"] == row["created_at"] or row["updated_at"] > row["created_at"] for row in stored)
    page = client.get("/admin/playlists")
    html(page)
    assert page.text.index(f"/admin/playlists/{first}") < page.text.index(f"/admin/playlists/{second}")


@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize("name,description", [("", "Manter"), ("   ", "Manter"), ("x" * 201, "Manter"), ("Nome", "x" * 1001)])
def test_invalid_playlist_form_preserves_values(client, isolated_database, editing, name, description):
    playlist_id = create(client) if editing else None
    before = snapshot(isolated_database)
    url = f"/admin/playlists/{playlist_id}/edit" if editing else "/admin/playlists"
    response = client.post(url, data={"name": name, "description": description})
    html(response, 422)
    assert f'value="{name}"' in response.text
    assert description in response.text
    assert snapshot(isolated_database) == before


def test_edit_preserves_items_assignments_and_creation(client, assets, screens, isolated_database):
    playlist_id = create(client)
    redirected(add(client, playlist_id, assets["image"]))
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    previous = rows(isolated_database, Playlist)[0]
    unchanged = {model.__name__: rows(isolated_database, model) for model in (PlaylistItem, ScreenPlaylistAssignment, MediaAsset)}
    response = client.post(f"/admin/playlists/{playlist_id}/edit", data={"name": " Novo nome ", "description": "Nova descrição"}, follow_redirects=False)
    redirected(response, f"/admin/playlists/{playlist_id}")
    stored = rows(isolated_database, Playlist)[0]
    assert stored["name"] == "Novo nome" and stored["description"] == "Nova descrição"
    assert stored["created_at"] == previous["created_at"] and stored["updated_at"] > previous["updated_at"]
    assert unchanged == {model.__name__: rows(isolated_database, model) for model in (PlaylistItem, ScreenPlaylistAssignment, MediaAsset)}


def test_toggle_without_assignment_and_edit_inactive(client, assets, isolated_database):
    playlist_id = create(client)
    redirected(client.post(f"/admin/playlists/{playlist_id}/toggle", follow_redirects=False))
    assert rows(isolated_database, Playlist)[0]["active"] is False
    redirected(add(client, playlist_id, assets["image"], 20))
    redirected(add(client, playlist_id, assets["video"]))
    item_ids = [row["id"] for row in ordered(isolated_database, playlist_id)]
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{item_ids[1]}/move-up", follow_redirects=False))
    assert_order(isolated_database, playlist_id, list(reversed(item_ids)))
    redirected(client.post(f"/admin/playlists/{playlist_id}/edit", data={"name": "Inativa editada"}, follow_redirects=False))
    redirected(client.post(f"/admin/playlists/{playlist_id}/toggle", follow_redirects=False))
    assert rows(isolated_database, Playlist)[0]["active"] is True


@pytest.mark.parametrize("duration,expected", [(MISSING, 15), ("", 15), ("  ", 15), ("5", 5), ("600", 600), ("25", 25)])
def test_image_durations(client, assets, isolated_database, duration, expected):
    playlist_id = create(client)
    redirected(add(client, playlist_id, assets["image"], duration))
    assert ordered(isolated_database, playlist_id)[0]["duration_seconds"] == expected


@pytest.mark.parametrize("duration", ["4", "601", "abc", "5.5", "1e2", "true", "-5", "9" * 5000])
def test_invalid_image_duration_is_html_without_partial_insert(client, assets, isolated_database, duration):
    playlist_id = create(client)
    before = snapshot(isolated_database)
    response = add(client, playlist_id, assets["image"], duration)
    html(response, 422)
    assert "inteiro entre 5 e 600" in response.text
    assert f'value="{duration}"' in response.text
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("duration", [True, False, 5.0, [], {}, object()])
def test_service_rejects_other_duration_types(client, assets, isolated_database, duration):
    playlist_id = create(client)
    with Session(isolated_database) as session:
        with pytest.raises(playlists.PlaylistError) as rejected:
            playlists.add_item(playlist_id, assets["image"], duration, session)
        assert rejected.value.status_code == 422
    assert ordered(isolated_database, playlist_id) == []


@pytest.mark.parametrize("duration", ["", "15", "1.25", "0"])
def test_video_rejects_any_explicit_duration(client, assets, isolated_database, duration):
    playlist_id = create(client)
    before = snapshot(isolated_database)
    response = add(client, playlist_id, assets["video"], duration)
    html(response, 422)
    assert "reprodução integral" in response.text
    assert snapshot(isolated_database) == before


def test_video_integral_and_duplicate_media_across_playlists(client, assets, isolated_database):
    first, second = create(client), create(client)
    for playlist_id in (first, first, second):
        redirected(add(client, playlist_id, assets["video"]))
    assert len(rows(isolated_database, MediaAsset)) == 2
    assert len(rows(isolated_database, PlaylistItem)) == 3
    assert all(row["duration_seconds"] is None for row in rows(isolated_database, PlaylistItem))
    page = client.get(f"/admin/playlists/{first}")
    html(page)
    assert page.text.count("Reprodução integral (") == 2
    assert_order(isolated_database, first, [row["id"] for row in ordered(isolated_database, first)])


def seed_items(engine, playlist_id, media_id, count):
    with Session(engine) as session:
        session.add_all(PlaylistItem(playlist_id=playlist_id, media_id=media_id, position=position, duration_seconds=15)
                        for position in range(1, count + 1))
        session.commit()


def test_limit_of_100_counts_repetitions_and_never_partially_inserts(client, assets, isolated_database):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 99)
    redirected(add(client, playlist_id, assets["image"]))
    before = snapshot(isolated_database)
    response = add(client, playlist_id, assets["image"])
    html(response, 409)
    assert "no máximo 100" in response.text
    assert snapshot(isolated_database) == before
    assert [row["position"] for row in ordered(isolated_database, playlist_id)] == list(range(1, 101))


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("direction,path", [(-1, "move-up"), (1, "move-down")])
def test_move_beginning_middle_end_and_boundaries(client, assets, isolated_database, index, direction, path):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 3)
    expected = [row["id"] for row in ordered(isolated_database, playlist_id)]
    selected = expected[index]
    target = index + direction
    before = rows(isolated_database, Playlist)[0]
    if 0 <= target < len(expected):
        expected[index], expected[target] = expected[target], expected[index]
    response = client.post(f"/admin/playlists/{playlist_id}/items/{selected}/{path}", follow_redirects=False)
    redirected(response)
    assert_order(isolated_database, playlist_id, expected)
    after = rows(isolated_database, Playlist)[0]
    assert after["created_at"] == before["created_at"]
    if 0 <= target < 3:
        assert after["updated_at"] > before["updated_at"]
    else:
        assert after == before


@pytest.mark.parametrize("index", [0, 1, 3])
def test_remove_compacts_reordered_ids_without_removing_media(client, assets, isolated_database, isolated_media, index):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 4)
    initial = [row["id"] for row in ordered(isolated_database, playlist_id)]
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{initial[3]}/move-up", follow_redirects=False))
    expected = [initial[0], initial[1], initial[3], initial[2]]
    media_before = rows(isolated_database, MediaAsset)
    files_before = {path.name: path.read_bytes() for path in isolated_media.directory.iterdir()}
    removed = expected.pop(index)
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{removed}/remove", follow_redirects=False))
    assert_order(isolated_database, playlist_id, expected)
    assert rows(isolated_database, MediaAsset) == media_before
    assert {path.name: path.read_bytes() for path in isolated_media.directory.iterdir()} == files_before


def test_assign_replace_share_unassign_preserves_screen_and_timestamps(client, assets, screens, isolated_database):
    first, second = create(client), create(client)
    for playlist_id in (first, second):
        redirected(add(client, playlist_id, assets["image"]))
    client.patch(f"/api/screens/{screens[0]}", json={"active": False})
    original_screens = client.get("/api/screens").json()
    for screen_id in screens:
        redirected(client.post(f"/admin/screens/{screen_id}/playlist", data={"playlist_id": first}, follow_redirects=False),
                   f"/admin/screens/{screen_id}/playlist")
    initial = rows(isolated_database, ScreenPlaylistAssignment)
    assert [row["playlist_id"] for row in initial] == [first, first]
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": second}, follow_redirects=False))
    updated = rows(isolated_database, ScreenPlaylistAssignment)
    assert [row["playlist_id"] for row in updated] == [second, first]
    assert updated[0]["assigned_at"] == initial[0]["assigned_at"]
    assert updated[0]["updated_at"] > initial[0]["updated_at"]
    assert updated[1] == initial[1]
    for _ in range(2):
        redirected(client.post(f"/admin/screens/{screens[0]}/playlist/unassign", follow_redirects=False))
    assert rows(isolated_database, ScreenPlaylistAssignment) == [initial[1]]
    assert client.get("/api/screens").json() == original_screens
    assert len(rows(isolated_database, PlaylistItem)) == 2
    assert len(rows(isolated_database, Playlist)) == 2


@pytest.mark.parametrize("invalid_state", ["empty", "inactive"])
def test_invalid_assignment_keeps_previous_link(client, assets, screens, isolated_database, invalid_state):
    first, invalid = create(client), create(client)
    redirected(add(client, first, assets["image"]))
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": first}, follow_redirects=False))
    if invalid_state == "inactive":
        redirected(add(client, invalid, assets["image"]))
        redirected(client.post(f"/admin/playlists/{invalid}/toggle", follow_redirects=False))
    before = snapshot(isolated_database)
    response = client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": invalid})
    html(response, 409)
    assert "ativa e com pelo menos um item" in response.text
    assert f'value="{invalid}" selected' in response.text
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("action", ["deactivate", "remove-last"])
def test_assigned_playlist_cannot_become_inactive_or_empty(client, assets, screens, isolated_database, action):
    playlist_id = create(client)
    redirected(add(client, playlist_id, assets["image"]))
    for screen_id in screens:
        redirected(client.post(f"/admin/screens/{screen_id}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    item_id = ordered(isolated_database, playlist_id)[0]["id"]
    url = f"/admin/playlists/{playlist_id}/toggle" if action == "deactivate" else f"/admin/playlists/{playlist_id}/items/{item_id}/remove"
    before = snapshot(isolated_database)
    html(client.post(url), 409)
    assert snapshot(isolated_database) == before
    assert "Telas associadas (2)" in client.get(f"/admin/playlists/{playlist_id}").text


def test_shared_playlist_can_remove_nonlast_and_screen_toggle_keeps_assignment(client, assets, screens, isolated_database):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 2)
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    previous = rows(isolated_database, ScreenPlaylistAssignment)
    client.post(f"/admin/screens/{screens[0]}/toggle")
    assert rows(isolated_database, ScreenPlaylistAssignment) == previous
    first = ordered(isolated_database, playlist_id)[0]["id"]
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{first}/remove", follow_redirects=False))
    assert len(ordered(isolated_database, playlist_id)) == 1
    assert rows(isolated_database, ScreenPlaylistAssignment) == previous


@pytest.mark.parametrize("method,path,data", [
    ("GET", "/admin/playlists/999", {}), ("GET", "/admin/playlists/invalid/edit", {}),
    ("POST", "/admin/playlists/999/edit", {"name": "Nova"}), ("POST", "/admin/playlists/999/toggle", {}),
    ("POST", "/admin/playlists/999/items", {"media_id": "1"}),
    ("POST", "/admin/playlists/1/items/999/remove", {}),
    ("POST", "/admin/playlists/1/items/999/move-up", {}),
    ("POST", "/admin/playlists/1/items/999/move-down", {}),
    ("GET", "/admin/screens/999/playlist", {}), ("POST", "/admin/screens/999/playlist", {"playlist_id": "1"}),
    ("POST", "/admin/screens/999/playlist/unassign", {}),
    ("POST", "/admin/playlists/1/items", {"media_id": "999"}),
    ("GET", "/admin/playlists/999999999999999999999999999999", {}),
])
def test_missing_records_are_html_and_never_modify_data(client, isolated_database, method, path, data):
    create(client)
    before = snapshot(isolated_database)
    html(client.request(method, path, data=data), 404)
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("action", ["remove", "move-up", "move-down"])
def test_item_of_another_playlist_cannot_be_modified(client, assets, isolated_database, action):
    first, second = create(client), create(client)
    redirected(add(client, second, assets["image"]))
    item_id = ordered(isolated_database, second)[0]["id"]
    before = snapshot(isolated_database)
    html(client.post(f"/admin/playlists/{first}/items/{item_id}/{action}"), 404)
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("table,values", [
    ("item", {"playlist_id": 999}), ("item", {"media_id": 999}),
    ("item", {"playlist_id": None}), ("item", {"media_id": None}),
    ("item", {"position": 0}), ("item", {"position": -1}), ("item", {"position": 1.5}),
    ("item", {"duration_seconds": 4}), ("item", {"duration_seconds": 601}), ("item", {"duration_seconds": 10.5}),
    ("assignment", {"screen_id": 999}), ("assignment", {"playlist_id": 999}),
    ("playlist", {"name": "  "}), ("playlist", {"name": "x" * 201}),
    ("playlist", {"description": "x" * 1001}),
])
def test_sql_constraints_and_foreign_keys(client, assets, screens, isolated_database, table, values):
    playlist_id = create(client)
    records = {
        "item": (PlaylistItem, {"playlist_id": playlist_id, "media_id": assets["image"], "position": 1, "duration_seconds": 15}),
        "assignment": (ScreenPlaylistAssignment, {"screen_id": screens[0], "playlist_id": playlist_id}),
        "playlist": (Playlist, {"name": "Válida", "description": None, "active": True}),
    }
    model, defaults = records[table]
    before = snapshot(isolated_database)
    with isolated_database.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(model.__table__.insert().values(**{**defaults, **values}))
    assert snapshot(isolated_database) == before


def test_unique_positions_and_screen_assignment_are_enforced(client, assets, screens, isolated_database):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 2)
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    before = snapshot(isolated_database)
    with Session(isolated_database) as session:
        session.add(PlaylistItem(playlist_id=playlist_id, media_id=assets["image"], position=1, duration_seconds=15))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    with isolated_database.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(ScreenPlaylistAssignment.__table__.insert().values(screen_id=screens[0], playlist_id=playlist_id))
        # Prova da colisão imediata que o swap de três flushes evita.
        with pytest.raises(IntegrityError):
            connection.exec_driver_sql("UPDATE playlist_items SET position=2 WHERE playlist_id=? AND position=1", (playlist_id,))
    assert snapshot(isolated_database) == before
    first = ordered(isolated_database, playlist_id)[0]["id"]
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{first}/move-down", follow_redirects=False))
    assert [row["position"] for row in ordered(isolated_database, playlist_id)] == [1, 2]


def test_foreign_keys_on_every_connection_and_after_reconnect(client, isolated_database):
    connections = [isolated_database.connect() for _ in range(3)]
    try:
        assert all(connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1 for connection in connections)
    finally:
        for connection in connections:
            connection.close()
    isolated_database.dispose()
    with isolated_database.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


@pytest.mark.parametrize("operation", ["remove", "move-down"])
def test_mid_reorder_failure_rolls_back_every_position(client, assets, isolated_database, operation):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 4)
    initial = [row["id"] for row in ordered(isolated_database, playlist_id)]
    before = snapshot(isolated_database)
    updates = []

    def fail_second_update(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE playlist_items"):
            updates.append(statement)
            if len(updates) == 2:
                raise OperationalError("forced test failure", {}, RuntimeError("isolated"))

    event.listen(isolated_database, "before_cursor_execute", fail_second_update)
    try:
        response = client.post(f"/admin/playlists/{playlist_id}/items/{initial[0]}/{operation}")
    finally:
        event.remove(isolated_database, "before_cursor_execute", fail_second_update)
    html(response, 409)
    assert len(updates) == 2
    assert snapshot(isolated_database) == before
    assert_order(isolated_database, playlist_id, initial)


@pytest.mark.parametrize("operation", ["create", "edit", "add", "toggle", "remove", "move", "replace", "unassign"])
def test_commit_failure_rolls_back_entire_operation(client, assets, screens, isolated_database, monkeypatch, operation):
    first, second = create(client), create(client)
    seed_items(isolated_database, first, assets["image"], 3)
    seed_items(isolated_database, second, assets["image"], 1)
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": first}, follow_redirects=False))
    item_id = ordered(isolated_database, first)[0]["id"]
    operations = {
        "create": ("/admin/playlists", {"name": "Falha"}),
        "edit": (f"/admin/playlists/{first}/edit", {"name": "Alteração"}),
        "add": (f"/admin/playlists/{first}/items", {"media_id": assets["image"]}),
        "toggle": (f"/admin/playlists/{second}/toggle", {}),
        "remove": (f"/admin/playlists/{first}/items/{item_id}/remove", {}),
        "move": (f"/admin/playlists/{first}/items/{item_id}/move-down", {}),
        "replace": (f"/admin/screens/{screens[0]}/playlist", {"playlist_id": second}),
        "unassign": (f"/admin/screens/{screens[0]}/playlist/unassign", {}),
    }
    before = snapshot(isolated_database)

    def fail_commit(session):
        raise SQLAlchemyError("private database parameters must not appear")

    monkeypatch.setattr(Session, "commit", fail_commit)
    path, data = operations[operation]
    response = client.post(path, data=data)
    html(response, 503)
    assert "private database parameters" not in response.text
    assert snapshot(isolated_database) == before


def test_all_gets_and_wrong_methods_leave_database_and_files_unchanged(client, assets, screens, isolated_database, isolated_media):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 1)
    before = snapshot(isolated_database)
    files_before = {path.name: path.read_bytes() for path in isolated_media.directory.iterdir()}
    for path in GET_PATHS:
        html(client.get(path))
    for path in POST_PATHS:
        if path not in GET_PATHS:
            assert client.get(path).status_code == 405
        assert client.delete(path).status_code in (404, 405)
    assert snapshot(isolated_database) == before
    assert {path.name: path.read_bytes() for path in isolated_media.directory.iterdir()} == files_before


@pytest.mark.parametrize("path", GET_PATHS)
def test_anonymous_get_redirects_without_writes(anonymous_client, isolated_database, path):
    before = snapshot(isolated_database)
    response = anonymous_client.get(path, follow_redirects=False)
    redirected(response, "/admin/login")
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("path", POST_PATHS)
def test_anonymous_posts_never_write(anonymous_client, isolated_database, path):
    before = snapshot(isolated_database)
    html(anonymous_client.post(path, data={"name": "Não criar", "media_id": "1", "playlist_id": "1"}), 401)
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("path", POST_PATHS)
@pytest.mark.parametrize("csrf", [None, "wrong", "x" * 43])
def test_every_post_requires_session_csrf(client, isolated_database, path, csrf):
    before = snapshot(isolated_database)
    data = {"name": "Não criar", "media_id": "1", "playlist_id": "1"}
    if csrf is not None:
        data["csrf_token"] = csrf
    response = TestClient.request(client, "POST", path, data=data)
    html(response, 403)
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("method,path", [("GET", path) for path in GET_PATHS] + [("POST", path) for path in POST_PATHS])
def test_viewer_is_refused_everywhere(client, isolated_database, method, path):
    with Session(isolated_database) as session:
        session.scalar(select(User)).role = "viewer"
        session.commit()
    before = snapshot(isolated_database)
    html(client.request(method, path), 403)
    assert snapshot(isolated_database) == before


class Forms(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.forms = []
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {"method": attrs.get("method"), "fields": {}}
            self.forms.append(self.current)
        elif tag in {"input", "select"} and self.current is not None and "name" in attrs:
            self.current["fields"][attrs["name"]] = attrs.get("value")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


def test_every_rendered_form_has_csrf_video_has_no_duration_and_screens_show_links(client, assets, screens, isolated_database):
    playlist_id = create(client)
    for kind in ("image", "video"):
        redirected(add(client, playlist_id, assets[kind]))
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    for path in GET_PATHS:
        page = client.get(path)
        html(page)
        for form in Forms(page.text).forms:
            assert form["method"] == "post"
            assert form["fields"]["csrf_token"] == client.csrf_token
    detail = client.get(f"/admin/playlists/{playlist_id}")
    additions = [form for form in Forms(detail.text).forms if "media_id" in form["fields"]]
    assert len(additions) == 2
    assert "duration_seconds" not in additions[0]["fields"]
    assert additions[1]["fields"]["duration_seconds"] == "15"
    screen_list = client.get("/admin/screens").text
    assert "Playlist Piloto 007" in screen_list and "Sem playlist" in screen_list
    for screen_id in screens:
        assert f"/admin/screens/{screen_id}/playlist" in screen_list


def test_malicious_names_descriptions_and_media_titles_are_escaped(client, assets, screens, isolated_database):
    malicious = '<script>alert("x")</script>'
    playlist_id = create(client, malicious, "</textarea>" + malicious)
    with Session(isolated_database) as session:
        session.get(MediaAsset, assets["image"]).title = malicious
        session.commit()
    redirected(add(client, playlist_id, assets["image"]))
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    for path in ("/admin/playlists", f"/admin/playlists/{playlist_id}", f"/admin/playlists/{playlist_id}/edit",
                 "/admin/screens", f"/admin/screens/{screens[0]}/playlist"):
        response = client.get(path)
        html(response)
        assert malicious not in response.text
        assert "&lt;script&gt;" in response.text
        assert "script-src 'none'" in response.headers["content-security-policy"]


def test_repeated_initialization_preserves_all_tables_and_api_contract(client, assets, screens, isolated_database):
    playlist_id = create(client)
    redirected(add(client, playlist_id, assets["image"]))
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": playlist_id}, follow_redirects=False))
    expected_screens = client.get("/api/screens").json()
    before = snapshot(isolated_database)
    for _ in range(2):
        with TestClient(app, base_url="https://testserver") as restarted:
            restarted.cookies.update(client.cookies)
            html(restarted.get(f"/admin/playlists/{playlist_id}"))
            assert restarted.get("/api/screens").json() == expected_screens
            ranged = restarted.get(f"/media/{assets['image']}/file", headers={"Range": "bytes=0-1"})
            assert ranged.status_code == 206 and len(ranged.content) == 2
    assert snapshot(isolated_database) == before
    assert {"playlists", "playlist_items", "screen_playlist_assignments"} <= set(inspect(isolated_database).get_table_names())


def race(engine, operations):
    barrier = Barrier(len(operations))

    def perform(operation):
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                operation(session)
                return "ok"
            except playlists.PlaylistError as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(perform, operations))


def test_concurrent_addition_never_exceeds_limit(client, assets, isolated_database):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 99)
    operations = [lambda session: playlists.add_item(playlist_id, assets["image"], None, session)] * 2
    assert sorted(race(isolated_database, operations), key=str) == [409, "ok"]
    assert [row["position"] for row in ordered(isolated_database, playlist_id)] == list(range(1, 101))


@pytest.mark.parametrize("other_action", ["remove", "deactivate"])
def test_concurrent_assignment_cannot_bind_empty_or_inactive_playlist(client, assets, screens, isolated_database, other_action):
    playlist_id = create(client)
    seed_items(isolated_database, playlist_id, assets["image"], 1)
    item_id = ordered(isolated_database, playlist_id)[0]["id"]
    operations = [lambda session: playlists.assign_playlist(screens[0], playlist_id, session)]
    if other_action == "remove":
        operations.append(lambda session: playlists.remove_item(playlist_id, item_id, session))
    else:
        operations.append(lambda session: playlists.toggle_playlist(playlist_id, session))
    assert sorted(race(isolated_database, operations), key=str) == [409, "ok"]
    assignments = rows(isolated_database, ScreenPlaylistAssignment)
    if assignments:
        assert rows(isolated_database, Playlist)[0]["active"]
        assert len(ordered(isolated_database, playlist_id)) == 1


@pytest.mark.parametrize("field,value", [("media_id", "abc"), ("media_id", "1.5"), ("media_id", "true")])
def test_invalid_media_identifier_is_html(client, isolated_database, field, value):
    playlist_id = create(client)
    before = snapshot(isolated_database)
    html(client.post(f"/admin/playlists/{playlist_id}/items", data={field: value}), 422)
    assert snapshot(isolated_database) == before


def test_file_in_text_field_is_rejected_as_html(client, isolated_database):
    before = snapshot(isolated_database)
    response = client.post("/admin/playlists", files={"name": ("name.txt", b"invalid field")})
    html(response, 422)
    assert snapshot(isolated_database) == before


def test_unassigned_last_item_can_be_removed_and_no_public_playlist_api_exists(client, assets, isolated_database, anonymous_client):
    playlist_id = create(client)
    redirected(add(client, playlist_id, assets["image"]))
    item_id = ordered(isolated_database, playlist_id)[0]["id"]
    redirected(client.post(f"/admin/playlists/{playlist_id}/items/{item_id}/remove", follow_redirects=False))
    assert ordered(isolated_database, playlist_id) == []
    assert len(rows(isolated_database, MediaAsset)) == 2
    for path in ("/api/playlists", "/player/tv-piloto", "/api/devices", "/manifest/tv-piloto"):
        assert anonymous_client.get(path).status_code == 404


def test_valid_assignment_options_and_reassigning_same_playlist_is_idempotent(client, assets, screens, isolated_database):
    valid, empty, inactive = create(client, "Disponível"), create(client, "Vazia"), create(client, "Inativa")
    for playlist_id in (valid, inactive):
        redirected(add(client, playlist_id, assets["image"]))
    redirected(client.post(f"/admin/playlists/{inactive}/toggle", follow_redirects=False))
    response = client.get(f"/admin/screens/{screens[0]}/playlist")
    html(response)
    assert f'<option value="{valid}"' in response.text
    assert f'<option value="{empty}"' not in response.text
    assert f'<option value="{inactive}"' not in response.text
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": valid}, follow_redirects=False))
    before = snapshot(isolated_database)
    redirected(client.post(f"/admin/screens/{screens[0]}/playlist", data={"playlist_id": valid}, follow_redirects=False))
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("state", ["revoked", "absolute-expiry", "idle-expiry", "inactive-user"])
def test_new_routes_reuse_existing_session_policy(client, isolated_database, method, state):
    with Session(isolated_database) as session:
        auth_session = session.scalar(select(AuthSession))
        if state == "revoked":
            auth_session.revoked = True
        elif state == "absolute-expiry":
            auth_session.expires_at = datetime(2026, 10, 14, 11, 59)
        elif state == "idle-expiry":
            auth_session.last_activity_at = datetime(2026, 10, 14, 11)
        else:
            session.scalar(select(User)).active = False
        session.commit()
    before = snapshot(isolated_database)
    response = client.request(method, "/admin/playlists", data={"name": "Não criar"}, follow_redirects=False)
    if method == "GET":
        redirected(response, "/admin/login")
    else:
        html(response, 401)
    assert snapshot(isolated_database) == before
