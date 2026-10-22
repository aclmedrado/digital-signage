from datetime import timedelta

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, inspect, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base
from app.main import app
from app.models import (MediaAsset, Playlist, PlaylistItem, Screen,
                        ScreenDeviceSession, ScreenPairingCode, ScreenPlaylistAssignment, User)
from app.services import auth, device_auth, playlists
from tests.player_helpers import activate, issue, seed, service_activate, service_code
from tests.test_playlists import rows, snapshot


@pytest.fixture
def data(client, isolated_database, isolated_media):
    return seed(isolated_database, isolated_media)


@pytest.fixture
def paired(client, anonymous_client, data):
    assert activate(anonymous_client, issue(client, data["screens"][0])).status_code == 303
    return anonymous_client


def test_order_repetition_duration_stable_revision_and_no_private_fields(paired, data, isolated_database):
    before = snapshot(isolated_database)
    first = paired.get("/player/s/tv-piloto/manifest")
    assert first.status_code == 200
    manifest = first.json()
    assert manifest["state"] == "playing" and manifest["poll_after_seconds"] == 20
    assert manifest["screen"] == {"name": "tv-piloto", "slug": "tv-piloto"}
    assert [item["id"] for item in manifest["items"]] == data["items"]
    assert [item["duration_seconds"] for item in manifest["items"]] == [6, None, 8]
    assert [item["kind"] for item in manifest["items"]] == ["image", "video", "image"]
    assert manifest["items"][0]["url"] == manifest["items"][2]["url"]
    assert len(manifest["revision"]) == 64
    assert paired.get("/player/s/tv-piloto/manifest").json() == manifest
    for forbidden in ("/app/", "stored_filename", "token", "password", "tv-patio", "original_filename"):
        assert forbidden not in first.text
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("change", ["screen-name", "screen-inactive", "playlist-name", "playlist-inactive",
                                   "duration", "order", "remove", "add", "replace", "unassign", "metadata"])
def test_revision_changes_with_relevant_data(paired, data, isolated_database, change):
    before = paired.get("/player/s/tv-piloto/manifest").json()["revision"]
    with Session(isolated_database) as session:
        if change == "screen-name":
            session.get(Screen, data["screens"][0]).name = "Novo nome"
        elif change == "screen-inactive":
            session.get(Screen, data["screens"][0]).active = False
        elif change == "playlist-name":
            session.get(Playlist, data["playlist"]).name = "Nova campanha"
        elif change == "playlist-inactive":
            session.get(Playlist, data["playlist"]).active = False
        elif change == "duration":
            session.get(PlaylistItem, data["items"][0]).duration_seconds = 30
        elif change == "metadata":
            session.get(MediaAsset, data["assets"][0]).title = "Novo título"
        elif change == "replace":
            replacement = Playlist(name="Outra playlist")
            session.add(replacement)
            session.flush()
            session.add(PlaylistItem(playlist_id=replacement.id, media_id=data["assets"][0], position=1, duration_seconds=15))
            session.get(ScreenPlaylistAssignment, data["screens"][0]).playlist_id = replacement.id
        elif change == "unassign":
            session.delete(session.get(ScreenPlaylistAssignment, data["screens"][0]))
        elif change == "order":
            playlists.move_item(data["playlist"], data["items"][0], 1, session)
        elif change == "remove":
            playlists.remove_item(data["playlist"], data["items"][0], session)
        elif change == "add":
            playlists.add_item(data["playlist"], data["assets"][0], 12, session)
        session.commit()
    after = paired.get("/player/s/tv-piloto/manifest").json()
    assert after["revision"] != before
    assert paired.get("/player/s/tv-piloto/manifest").json()["revision"] == after["revision"]


@pytest.mark.parametrize("state", ["screen_inactive", "no_playlist", "playlist_unavailable", "empty"])
def test_neutral_states_never_expose_media(paired, data, isolated_database, state):
    with Session(isolated_database) as session:
        if state == "screen_inactive":
            session.get(Screen, data["screens"][0]).active = False
        elif state == "no_playlist":
            session.delete(session.get(ScreenPlaylistAssignment, data["screens"][0]))
        elif state == "playlist_unavailable":
            session.get(Playlist, data["playlist"]).active = False
        else:
            for item in session.scalars(select(PlaylistItem)):
                session.delete(item)
        session.commit()
    response = paired.get("/player/s/tv-piloto/manifest")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["state"] == ("playlist_unavailable" if state == "empty" else state)
    assert "/media/" not in response.text
    assert paired.get(f"/player/s/tv-piloto/media/{data['assets'][0]}").status_code == 404


@pytest.mark.parametrize("suffix", ["", "/manifest", "/media/1"])
def test_same_shared_playlist_does_not_authorize_other_screen(paired, suffix):
    response = paired.get("/player/s/tv-patio" + suffix, follow_redirects=False)
    assert response.status_code == 403
    assert "tv-patio" not in response.text and "items" not in response.text


@pytest.mark.parametrize("path,status", [
    ("/admin", 303), ("/admin/screens", 303), ("/admin/media", 303), ("/admin/playlists", 303),
    ("/admin/screens/1/player", 303), ("/api/screens", 401), ("/media/1/file", 401),
])
def test_device_cookie_never_authorizes_admin(paired, path, status):
    assert paired.get(path, follow_redirects=False).status_code == status


@pytest.mark.parametrize("path", ["/api/screens", "/admin/screens", "/admin/media", "/admin/playlists",
                                  "/admin/screens/1/player/pairing", "/admin/screens/1/player/revoke"])
def test_device_cookie_and_its_challenge_never_satisfy_admin_writes(paired, path, isolated_database):
    before = snapshot(isolated_database)
    response = paired.post(path, data={"csrf_token": "x" * 43}, follow_redirects=False)
    assert response.status_code == 401
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("slug", ["tv-piloto", "unknown"])
def test_anonymous_manifest_and_media_deny_without_information(client, anonymous_client, data, slug):
    for suffix in ("/manifest", "/media/1"):
        response = anonymous_client.get(f"/player/s/{slug}{suffix}")
        assert response.status_code == 401 and "items" not in response.text
    response = anonymous_client.get(f"/player/s/{slug}", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/device/activate"


def test_admin_preview_does_not_pair_or_refresh_session(client, data, isolated_database):
    before = snapshot(isolated_database)
    for slug in ("tv-piloto", "tv-patio"):
        for suffix in ("", "/manifest", f"/media/{data['assets'][0]}"):
            response = client.get("/player/s/" + slug + suffix)
            assert response.status_code == 200
            assert "set-cookie" not in response.headers
    assert snapshot(isolated_database) == before
    assert client.get("/player/s/unknown/manifest").status_code == 404


@pytest.mark.parametrize("suffix", ["", "/manifest", "/media/1"])
def test_viewer_is_never_admin_preview(client, data, isolated_database, suffix):
    with Session(isolated_database) as session:
        session.scalar(select(User)).role = "viewer"
        session.commit()
    assert client.get("/player/s/tv-piloto" + suffix).status_code == 403


@pytest.mark.parametrize("failure", ["tampered", "hash", "expired", "revoked", "unknown"])
def test_invalid_device_cookie_denies_every_request(paired, data, isolated_database, monkeypatch, failure):
    cookie_name = app.state.auth_settings.device_cookie_name
    token = paired.cookies.get(cookie_name)
    if failure == "hash":
        token = rows(isolated_database, ScreenDeviceSession)[0]["token_hash"]
    elif failure == "tampered":
        token = ("A" if token[0] != "A" else "B") + token[1:]
    elif failure == "unknown":
        token = "A" * 43
    elif failure == "expired":
        now = app.state.auth_clock()
        monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(days=90))
    else:
        device_auth.revoke(isolated_database, str(data["screens"][0]))
    paired.cookies.clear()
    paired.cookies.set(cookie_name, token)
    before = snapshot(isolated_database)
    for suffix in ("", "/manifest", f"/media/{data['assets'][0]}"):
        response = paired.get("/player/s/tv-piloto" + suffix, follow_redirects=False)
        if failure == "hash" and not suffix:
            # Hash hexadecimal (64 caracteres) não é token válido (43).
            # Somente a página HTML orienta essa ausência de autenticação.
            assert response.status_code == 303
            assert response.headers["location"] == "/device/activate"
            assert response.content == b""
        else:
            assert response.status_code == (401 if failure == "hash" else 403)
            assert "location" not in response.headers
        assert "set-cookie" not in response.headers
        assert token not in response.text and "items" not in response.text
        assert "/player/s/" not in response.text
    assert snapshot(isolated_database) == before


def test_absolute_expiry_not_renewed_and_persists_between_apps(paired, isolated_database, monkeypatch):
    before = rows(isolated_database, ScreenDeviceSession)
    cookies = dict(paired.cookies)
    now = app.state.auth_clock()
    monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(days=89))
    isolated_database.dispose()
    with TestClient(app, base_url="https://testserver") as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get("/player/s/tv-piloto/manifest").status_code == 200
        assert rows(isolated_database, ScreenDeviceSession) == before
        monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(days=90))
        assert restarted.get("/player/s/tv-piloto/manifest").status_code == 403


def test_range_revalidated_and_admin_download_stays_private(paired, client, data):
    path = f"/player/s/tv-piloto/media/{data['assets'][1]}"
    response = paired.get(path, headers={"Range": "bytes=0-99"})
    assert response.status_code == 206 and len(response.content) == 100
    assert response.headers["content-length"] == "100"
    assert response.headers["content-range"] == "bytes 0-99/512"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert paired.get(path, headers={"Range": "bytes=512-"}).status_code == 416
    assert paired.get(path, headers={"Range": "not-bytes"}).status_code == 400
    assert paired.head(path).status_code == 405
    assert paired.get(f"/media/{data['assets'][1]}/file", headers={"Range": "bytes=0-99"}).status_code == 401
    assert client.get(f"/media/{data['assets'][1]}/file", headers={"Range": "bytes=0-99"}).status_code == 206


@pytest.mark.parametrize("failure", ["other-playlist", "missing-record", "missing-file", "invalid-path", "symlink"])
def test_media_guard_denies_noncurrent_or_missing_media(paired, data, isolated_database, isolated_media, tmp_path, failure):
    media_id = data["assets"][1]
    with Session(isolated_database) as session:
        asset = session.get(MediaAsset, media_id)
        if failure == "other-playlist":
            for item in session.scalars(select(PlaylistItem).where(PlaylistItem.media_id == media_id)):
                session.delete(item)
        elif failure == "missing-record":
            media_id = 999999
        elif failure == "missing-file":
            (isolated_media.directory / asset.stored_filename).unlink()
        elif failure == "invalid-path":
            asset.stored_filename = "../../secret.mp4"
        else:
            path = isolated_media.directory / asset.stored_filename
            path.unlink()
            outside = tmp_path / "outside.mp4"
            outside.write_bytes(b"private")
            path.symlink_to(outside)
        session.commit()
    response = paired.get(f"/player/s/tv-piloto/media/{media_id}")
    assert response.status_code == 404
    assert "/app/" not in response.text and "secret" not in response.text and "private" not in response.text


def test_replacing_assignment_immediately_removes_old_media_access(paired, data, isolated_database):
    with Session(isolated_database) as session:
        replacement = playlists.create_playlist("Só imagem", None, session)
        playlists.add_item(replacement, data["assets"][0], 15, session)
        playlists.assign_playlist(data["screens"][0], replacement, session)
    assert paired.get(f"/player/s/tv-piloto/media/{data['assets'][1]}", headers={"Range": "bytes=0-99"}).status_code == 404
    assert paired.get(f"/player/s/tv-piloto/media/{data['assets'][0]}").status_code == 200


def test_security_headers_and_static_assets(paired, client):
    page = paired.get("/player/s/tv-piloto")
    assert page.headers["cache-control"] == "private, no-store"
    assert page.headers["referrer-policy"] == "no-referrer"
    csp = page.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "/static/player.js" in page.text and "/static/player.css" in page.text
    assert "/admin" not in page.text and "token" not in page.text
    for path in ("/static/player.js", "/static/player.css"):
        assert paired.get(path).status_code == 200
    assert "script-src 'none'" in client.get("/admin/screens").headers["content-security-policy"]
    assert "script-src 'none'" in paired.get("/device/activate").headers["content-security-policy"]


@pytest.mark.parametrize("model,values", [
    (ScreenPairingCode, {"screen_id": 999999, "created_by_user_id": 1, "code_hash": "a" * 64}),
    (ScreenPairingCode, {"screen_id": 1, "created_by_user_id": 999999, "code_hash": "a" * 64}),
    (ScreenDeviceSession, {"screen_id": 999999, "token_hash": "a" * 64}),
])
def test_new_foreign_keys_enforced(client, data, isolated_database, model, values):
    now = auth.timestamp(app.state.auth_clock)
    with Session(isolated_database) as session:
        session.add(model(**values, created_at=now, expires_at=now + timedelta(minutes=10)))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_unique_codes_tokens_and_one_session_per_screen(client, data, isolated_database):
    for index in (0, 1):
        service_activate(isolated_database, app.state.auth_clock, service_code(isolated_database, app.state.auth_clock, data, index))
    now = auth.timestamp(app.state.auth_clock)
    with Session(isolated_database) as session:
        session.add(ScreenDeviceSession(screen_id=data["screens"][0], token_hash="a" * 64,
                                         created_at=now, expires_at=now + timedelta(days=1)))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    with Session(isolated_database) as session:
        devices = session.scalars(select(ScreenDeviceSession).order_by(ScreenDeviceSession.screen_id)).all()
        devices[1].token_hash = devices[0].token_hash
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    for index in (0, 1):
        service_code(isolated_database, app.state.auth_clock, data, index)
    with Session(isolated_database) as session:
        codes = session.scalars(select(ScreenPairingCode).order_by(ScreenPairingCode.screen_id)).all()
        codes[1].code_hash = codes[0].code_hash
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_incremental_schema_preserves_all_previous_data(client, data, isolated_database):
    service_activate(isolated_database, app.state.auth_clock, service_code(isolated_database, app.state.auth_clock, data))
    before = snapshot(isolated_database)
    for _ in range(2):
        Base.metadata.create_all(isolated_database)
    assert snapshot(isolated_database) == before
    assert {"screen_pairing_codes", "screen_device_sessions", "device_activation_challenges", "device_activation_limits"} <= set(inspect(isolated_database).get_table_names())
    with isolated_database.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_database_read_failure_denies_safely(paired, isolated_database):
    def fail(*args):
        raise SQLAlchemyError("private database parameters")
    event.listen(isolated_database, "before_cursor_execute", fail)
    try:
        response = paired.get("/player/s/tv-piloto/manifest")
    finally:
        event.remove(isolated_database, "before_cursor_execute", fail)
    assert response.status_code == 503
    assert "parameters" not in response.text and "Traceback" not in response.text


def test_admin_links_and_escaped_screen_name(client, data, isolated_database):
    with Session(isolated_database) as session:
        session.get(Screen, data["screens"][0]).name = '<script>alert("x")</script>'
        session.commit()
    page = client.get(f"/admin/screens/{data['screens'][0]}/player")
    assert "&lt;script&gt;" in page.text and "<script>" not in page.text
    assert "/player/s/tv-piloto" in page.text
    assert "Player / Pareamento" in client.get("/admin/screens").text


def test_query_tokens_never_authorize(anonymous_client):
    response = anonymous_client.get("/player/s/tv-piloto/manifest", params={"token": "A" * 43})
    assert response.status_code == 401
