from base64 import b32decode, urlsafe_b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.main import app
from app.models import (AuthSession, DeviceActivationChallenge, DeviceActivationLimit, LoginLimit,
                        Screen, ScreenDeviceSession, ScreenPairingCode, User)
from app.services import auth, device_auth
from tests.helpers import csrf_from
from tests.player_helpers import activate, issue, seed, service_activate, service_code
from tests.test_playlists import rows, snapshot


@pytest.fixture
def data(client, isolated_database, isolated_media):
    return seed(isolated_database, isolated_media)


@pytest.mark.parametrize("action", ["pairing", "revoke"])
def test_pairing_posts_require_admin_and_csrf(client, anonymous_client, isolated_database, action):
    path = f"/admin/screens/1/player/{action}"
    before = snapshot(isolated_database)
    assert anonymous_client.post(path).status_code == 401
    for token in (None, "bad", "x" * 43):
        fields = {"csrf_token": token} if token else {}
        assert TestClient.request(client, "POST", path, data=fields).status_code == 403
    assert snapshot(isolated_database) == before
    with Session(isolated_database) as session:
        session.scalar(select(User)).role = "viewer"
        session.commit()
    before = snapshot(isolated_database)
    assert client.post(path).status_code == 403
    assert snapshot(isolated_database) == before


def test_code_entropy_hash_and_one_response_only(client, data, isolated_database, caplog):
    screen = data["screens"][0]
    response = client.post(f"/admin/screens/{screen}/player/pairing")
    from tests.player_helpers import PairingCodeParser
    code = PairingCodeParser(response.text).code
    canonical = device_auth.normalized_code(code)
    assert len(b32decode(canonical + "======")) == 16
    stored = rows(isolated_database, ScreenPairingCode)[0]
    assert stored["code_hash"] == auth.token_hash(canonical)
    assert stored["created_by_user_id"] == data["user"]
    assert stored["expires_at"] - stored["created_at"] == timedelta(minutes=10)
    assert code not in str(snapshot(isolated_database)) and canonical not in str(snapshot(isolated_database))
    assert response.headers["cache-control"] == "no-store" and "location" not in response.headers
    page = client.get(f"/admin/screens/{screen}/player")
    assert code not in page.text and stored["code_hash"] not in page.text
    assert code not in caplog.text and canonical not in caplog.text
    assert 'name="csrf_token"' in page.text


def test_valid_activation_hash_cookie_and_single_use(client, anonymous_client, data, isolated_database):
    code = issue(client, data["screens"][0])
    response = activate(anonymous_client, code.lower().replace("-", " "))
    assert response.status_code == 303 and response.headers["location"] == "/player/s/tv-piloto"
    cookie = anonymous_client.cookies.get(app.state.auth_settings.device_cookie_name)
    assert len(urlsafe_b64decode(cookie + "=")) == 32
    stored = rows(isolated_database, ScreenDeviceSession)[0]
    assert stored["token_hash"] == auth.token_hash(cookie) and cookie not in str(stored)
    assert stored["expires_at"] - stored["created_at"] == timedelta(days=90)
    assert rows(isolated_database, ScreenPairingCode) == []
    header = next(h for h in response.headers.get_list("set-cookie") if "device=" in h)
    for flag in ("__Host-signage-device=", "Secure", "HttpOnly", "SameSite=lax", "Path=/", "Max-Age=7776000"):
        assert flag in header
    assert "Domain=" not in header
    assert activate(anonymous_client, code).status_code == 401


@pytest.mark.parametrize("failure", ["missing", "wrong", "unknown", "expired", "login-challenge", "replay"])
def test_activation_csrf_is_independent_and_single_use(client, anonymous_client, data, isolated_database, monkeypatch, failure):
    code = issue(client, data["screens"][0])
    page = anonymous_client.get("/device/activate")
    csrf = csrf_from(page)
    if failure == "missing":
        anonymous_client.cookies.clear()
    elif failure == "wrong":
        csrf = "x" * 43
    elif failure == "unknown":
        anonymous_client.cookies.set(app.state.auth_settings.activation_cookie_name, "x" * 43)
    elif failure == "expired":
        now = app.state.auth_clock()
        monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(minutes=10))
    elif failure == "login-challenge":
        csrf = csrf_from(anonymous_client.get("/admin/login"))
    elif failure == "replay":
        assert anonymous_client.post("/device/activate", data={"code": "wrong", "csrf_token": csrf}).status_code == 401
    before = rows(isolated_database, ScreenPairingCode)
    response = anonymous_client.post("/device/activate", data={"code": code, "csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 403
    assert rows(isolated_database, ScreenPairingCode) == before
    assert rows(isolated_database, ScreenDeviceSession) == []


@pytest.mark.parametrize("code", ["", "wrong", "A" * 26, "A" * 25 + "B", "!" * 26, "é" * 26, "x" * 129])
def test_invalid_codes_are_generic_without_reflection(client, anonymous_client, data, code):
    response = activate(anonymous_client, code)
    assert response.status_code == 401
    assert device_auth.INVALID_CODE in response.text
    assert "tv-piloto" not in response.text and "tv-patio" not in response.text
    assert "location" not in response.headers
    if code:
        assert 'value="' + code + '"' not in response.text


@pytest.mark.parametrize("reason", ["expired", "reissued", "screen-inactive"])
def test_unusable_code_cannot_create_session(client, anonymous_client, data, isolated_database, monkeypatch, reason):
    code = issue(client, data["screens"][0])
    if reason == "expired":
        now = app.state.auth_clock()
        monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(minutes=10))
    elif reason == "reissued":
        assert issue(client, data["screens"][0]) != code
    else:
        with Session(isolated_database) as session:
            session.get(Screen, data["screens"][0]).active = False
            session.commit()
    assert activate(anonymous_client, code).status_code == 401
    assert rows(isolated_database, ScreenDeviceSession) == []


def test_reissue_keeps_old_session_until_consumption(client, anonymous_client, data, isolated_database):
    assert activate(anonymous_client, issue(client, data["screens"][0])).status_code == 303
    previous = dict(anonymous_client.cookies)
    code = issue(client, data["screens"][0])
    assert anonymous_client.get("/player/s/tv-piloto/manifest").status_code == 200
    assert activate(anonymous_client, code).status_code == 303
    with TestClient(app, base_url="https://testserver") as old:
        old.cookies.update(previous)
        assert old.get("/player/s/tv-piloto/manifest").status_code == 403
    assert len(rows(isolated_database, ScreenDeviceSession)) == 1


def test_revoke_needs_confirmation_and_only_affects_target(client, anonymous_client, data, isolated_database):
    tokens = []
    for screen in data["screens"]:
        code = issue(client, screen)
        token, _ = service_activate(isolated_database, app.state.auth_clock, code)
        tokens.append(token)
    issue(client, data["screens"][0])
    path = f"/admin/screens/{data['screens'][0]}/player/revoke"
    before = snapshot(isolated_database)
    assert client.post(path).status_code == 422
    assert snapshot(isolated_database) == before
    assert client.post(path, data={"confirm": "revoke"}, follow_redirects=False).status_code == 303
    assert rows(isolated_database, ScreenPairingCode) == []
    anonymous_client.cookies.set(app.state.auth_settings.device_cookie_name, tokens[0])
    assert anonymous_client.get("/player/s/tv-piloto/manifest").status_code == 403
    anonymous_client.cookies.set(app.state.auth_settings.device_cookie_name, tokens[1])
    assert anonymous_client.get("/player/s/tv-patio/manifest").status_code == 200


def test_limit_persistent_window_and_untrusted_forwarded_for(client, anonymous_client, data, isolated_database, monkeypatch):
    login_limits = rows(isolated_database, LoginLimit)
    for number in range(10):
        assert activate(anonymous_client, "invalid", headers={"X-Forwarded-For": f"192.0.2.{number}"}).status_code == 401
    valid = issue(client, data["screens"][0])
    assert activate(anonymous_client, valid).status_code == 429
    assert rows(isolated_database, DeviceActivationLimit)[0]["failures"] == 10
    assert rows(isolated_database, LoginLimit) == login_limits
    isolated_database.dispose()
    with TestClient(app, base_url="https://testserver") as another:
        assert activate(another, "invalid").status_code == 429
    now = app.state.auth_clock()
    monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(minutes=15))
    valid = service_code(isolated_database, app.state.auth_clock, data)
    assert activate(anonymous_client, valid).status_code == 303
    assert rows(isolated_database, DeviceActivationLimit) == []


def test_concurrent_code_consumption_only_one_session(client, data, isolated_database):
    code = service_code(isolated_database, app.state.auth_clock, data)
    challenges = [device_auth.create_challenge(isolated_database, app.state.auth_clock) for _ in range(2)]
    barrier = Barrier(2)
    def consume(challenge):
        barrier.wait(timeout=5)
        try:
            return device_auth.activate(isolated_database, app.state.auth_clock, *challenge, code, "same-origin")[0]
        except auth.AuthError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(consume, challenges))
    assert sum(isinstance(value, str) for value in results) == 1
    assert sum(value == 401 for value in results) == 1
    assert len(rows(isolated_database, ScreenDeviceSession)) == 1
    assert rows(isolated_database, ScreenPairingCode) == []


@pytest.mark.parametrize("operation", ["issue", "consume", "revoke", "challenge"])
def test_commit_failure_rolls_back_no_secrets_in_error(client, data, isolated_database, monkeypatch, operation):
    code = service_code(isolated_database, app.state.auth_clock, data)
    service_activate(isolated_database, app.state.auth_clock, code)
    code = service_code(isolated_database, app.state.auth_clock, data)
    challenge = device_auth.create_challenge(isolated_database, app.state.auth_clock)
    before = snapshot(isolated_database)
    def fail(session):
        raise SQLAlchemyError("sensitive SQL parameters")
    with monkeypatch.context() as scoped:
        scoped.setattr(Session, "commit", fail)
        with pytest.raises(auth.AuthError) as caught:
            if operation == "issue":
                service_code(isolated_database, app.state.auth_clock, data)
            elif operation == "consume":
                device_auth.activate(isolated_database, app.state.auth_clock, *challenge, code, "isolated")
            elif operation == "revoke":
                device_auth.revoke(isolated_database, str(data["screens"][0]))
            else:
                device_auth.create_challenge(isolated_database, app.state.auth_clock)
        assert caught.value.status_code == 503 and "sensitive" not in str(caught.value)
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("path", ["/device/activate", "/player/s/tv-piloto", "/player/s/tv-piloto/manifest", "/player/s/tv-piloto/media/1"])
def test_transport_cannot_downgrade_or_trust_headers(anonymous_client, isolated_database, path):
    before = snapshot(isolated_database)
    response = anonymous_client.get("http://10.4.254.202:8080" + path, headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 503 and "set-cookie" not in response.headers
    assert snapshot(isolated_database) == before


def test_local_cookie_and_no_http_lan_exception(client, data, isolated_database, monkeypatch):
    code = service_code(isolated_database, app.state.auth_clock, data)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("LOCAL_AUTH_TEST_MODE", "true")
    with TestClient(app, base_url="http://localhost:18080") as local:
        response = activate(local, code)
        assert response.status_code == 303
        header = next(h for h in response.headers.get_list("set-cookie") if "local-device=" in h)
        assert "Secure" not in header and "Domain=" not in header
        for flag in ("HttpOnly", "SameSite=lax", "Path=/", "Max-Age=7776000"):
            assert flag in header
        assert local.get("/player/s/tv-piloto/manifest").status_code == 200
        assert local.get("http://10.4.254.202:8080/device/activate").status_code == 503


@pytest.mark.parametrize("body,content_type,status", [
    ("code=secret&csrf_token=x&code=again", "application/x-www-form-urlencoded", 403),
    ("code=secret", "application/x-www-form-urlencoded", 403),
    ('{"code":"secret"}', "application/json", 403),
    ("x" * 2049, "application/x-www-form-urlencoded", 413),
    (b"\xff", "application/x-www-form-urlencoded", 403),
])
def test_activation_body_bounded_and_not_reflected(anonymous_client, body, content_type, status):
    response = anonymous_client.post("/device/activate", content=body, headers={"Content-Type": content_type})
    assert response.status_code == status and "secret" not in response.text


def test_challenge_hashes_and_login_csrf_cannot_be_promoted(anonymous_client, isolated_database):
    page = anonymous_client.get("/device/activate")
    csrf = csrf_from(page)
    cookie = anonymous_client.cookies.get(app.state.auth_settings.activation_cookie_name)
    stored = rows(isolated_database, DeviceActivationChallenge)[0]
    assert stored["token_hash"] == auth.token_hash(cookie)
    assert stored["csrf_hash"] == auth.token_hash(csrf)
    assert cookie not in str(stored) and csrf not in str(stored)
    anonymous_client.cookies.set(app.state.auth_settings.session_cookie_name, cookie)
    assert anonymous_client.get("/api/screens").status_code == 401


def test_success_does_not_consume_failure_budget(client, data, isolated_database):
    for _ in range(12):
        service_activate(isolated_database, app.state.auth_clock,
                         service_code(isolated_database, app.state.auth_clock, data))
    assert rows(isolated_database, DeviceActivationLimit) == []


def test_concurrent_failures_cannot_bypass_origin_limit(client, data, isolated_database):
    challenges = [device_auth.create_challenge(isolated_database, app.state.auth_clock) for _ in range(12)]
    def fail(challenge):
        try:
            device_auth.activate(isolated_database, app.state.auth_clock, *challenge, "invalid", "shared")
        except auth.AuthError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fail, challenges))
    assert results.count(401) == 10 and results.count(429) == 2
    assert rows(isolated_database, DeviceActivationLimit)[0]["failures"] == 10


def test_expired_challenges_and_limits_are_cleaned(client, data, isolated_database, monkeypatch):
    for origin in ("one", "two"):
        with pytest.raises(auth.AuthError):
            service_activate(isolated_database, app.state.auth_clock, "invalid", origin)
    device_auth.create_challenge(isolated_database, app.state.auth_clock)
    now = app.state.auth_clock()
    monkeypatch.setattr(app.state, "auth_clock", lambda: now + timedelta(minutes=16))
    device_auth.create_challenge(isolated_database, app.state.auth_clock)
    assert len(rows(isolated_database, DeviceActivationChallenge)) == 1
    assert rows(isolated_database, DeviceActivationLimit) == []


@pytest.mark.parametrize("state", ["revoked", "expired", "idle", "inactive-user"])
@pytest.mark.parametrize("action", ["pairing", "revoke"])
def test_pairing_reuses_all_existing_admin_session_rules(client, data, isolated_database, state, action):
    with Session(isolated_database) as session:
        record = session.scalar(select(AuthSession))
        if state == "revoked":
            record.revoked = True
        elif state == "expired":
            record.expires_at = auth.timestamp(app.state.auth_clock)
        elif state == "idle":
            record.last_activity_at -= timedelta(minutes=30)
        else:
            session.get(User, record.user_id).active = False
        session.commit()
    before = snapshot(isolated_database)
    assert client.post(f"/admin/screens/{data['screens'][0]}/player/{action}").status_code == 401
    assert snapshot(isolated_database) == before


def test_code_and_session_generation_use_full_csprng_sizes(client, data, isolated_database, monkeypatch):
    calls = []
    original_bytes, original_urlsafe = device_auth.secrets.token_bytes, device_auth.secrets.token_urlsafe
    def random_bytes(size):
        calls.append(("bytes", size))
        return original_bytes(size)
    # token_urlsafe calls secrets.token_bytes internally; inspect >= sizes.
    def random_urlsafe(size):
        calls.append(("urlsafe", size))
        return original_urlsafe(size)
    monkeypatch.setattr(device_auth.secrets, "token_bytes", random_bytes)
    monkeypatch.setattr(device_auth.secrets, "token_urlsafe", random_urlsafe)
    service_activate(isolated_database, app.state.auth_clock,
                     service_code(isolated_database, app.state.auth_clock, data))
    assert ("bytes", 16) in calls
    assert calls.count(("urlsafe", 32)) == 3  # Cookie, CSRF, sessão.


def test_admin_pairing_get_requires_admin_without_writes(client, anonymous_client, data, isolated_database):
    path = f"/admin/screens/{data['screens'][0]}/player"
    before = snapshot(isolated_database)
    response = anonymous_client.get(path, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/admin/login"
    assert snapshot(isolated_database) == before
    with Session(isolated_database) as session:
        session.scalar(select(User)).role = "viewer"
        session.commit()
    before = snapshot(isolated_database)
    assert client.get(path).status_code == 403
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("screen_id", ["999999", "invalid", "9" * 100, "0"])
def test_unknown_screen_admin_pairing_is_generic_and_does_not_write(client, isolated_database, screen_id):
    before = snapshot(isolated_database)
    for suffix in ("", "/pairing", "/revoke"):
        path = f"/admin/screens/{screen_id}/player{suffix}"
        response = client.get(path) if not suffix else client.post(path, data={"confirm": "revoke"})
        assert response.status_code == 404
        assert "Traceback" not in response.text
    assert snapshot(isolated_database) == before
