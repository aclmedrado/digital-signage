from base64 import urlsafe_b64decode
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import getpass
from unittest.mock import Mock

from argon2 import Type, extract_parameters
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.config import AuthSettings, get_auth_settings
from app.database import Base
from app.main import app
from app.models import AuthSession, LoginChallenge, LoginLimit, MediaAsset, Screen, User
from app.scripts import bootstrap_admin as cli
from app.services import auth
from tests.helpers import CsrfInput, TEST_PASSWORD, TEST_USERNAME, csrf_from, ensure_admin

SCREEN = {"name": "TV Piloto", "slug": "tv-piloto", "location": "Sala"}


@pytest.fixture
def clock(monkeypatch):
    value = [datetime(2026, 10, 14, 12, tzinfo=timezone.utc)]
    monkeypatch.setattr(app.state, "auth_clock", lambda: value[0])
    return value


def snapshot(engine):
    with engine.connect() as connection:
        return {table.name: connection.execute(table.select().order_by(*table.primary_key)).all()
                for table in Base.metadata.sorted_tables}


def submit_login(client, username=TEST_USERNAME, password=TEST_PASSWORD, csrf=None):
    if csrf is None:
        csrf = csrf_from(client.get("/admin/login"))
    return client.post("/admin/login", data={"username": username, "password": password,
                       "csrf_token": csrf}, follow_redirects=False)


def test_startup_has_no_default_account(anonymous_client, isolated_database):
    with Session(isolated_database) as session:
        assert session.scalars(select(User)).all() == []
        assert session.scalars(select(AuthSession)).all() == []


def test_bootstrap_hash_and_normalization(anonymous_client, isolated_database):
    auth.bootstrap_admin(isolated_database, "  ADMIN-Test  ", TEST_PASSWORD)
    with Session(isolated_database) as session:
        user = session.scalar(select(User))
        assert user.username == TEST_USERNAME
        assert user.active and user.role == "admin"
        assert user.created_at and user.updated_at
        assert user.password_hash.startswith("$argon2id$")
        assert TEST_PASSWORD not in user.password_hash
        parameters = extract_parameters(user.password_hash)
        assert parameters.type == Type.ID
        assert parameters.memory_cost >= 19456
        assert parameters.time_cost >= 2
        assert parameters.parallelism == 1
        assert auth.verify_password(TEST_PASSWORD, user.password_hash)
        assert not auth.verify_password("incorrect", user.password_hash)


@pytest.mark.parametrize("username", [TEST_USERNAME, "second-admin"])
def test_bootstrap_repeated_never_overwrites(anonymous_client, isolated_database, username):
    ensure_admin(isolated_database)
    before = snapshot(isolated_database)
    with pytest.raises(auth.BootstrapError, match="Administrador já existe"):
        auth.bootstrap_admin(isolated_database, username, TEST_PASSWORD + "other")
    assert snapshot(isolated_database) == before


def test_concurrent_bootstrap_creates_only_one(anonymous_client, isolated_database):
    def create(username):
        try:
            auth.bootstrap_admin(isolated_database, username, TEST_PASSWORD)
            return True
        except auth.BootstrapError:
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(create, [TEST_USERNAME, "other-admin"])) == 1
    with Session(isolated_database) as session:
        assert len(session.scalars(select(User)).all()) == 1


@pytest.mark.parametrize("password", ["short", "a" * 16, "Aa1!" * 33])
def test_weak_bootstrap_password_rejected(anonymous_client, isolated_database, password):
    with pytest.raises(auth.BootstrapError, match="Senha:"):
        auth.bootstrap_admin(isolated_database, TEST_USERNAME, password)
    with Session(isolated_database) as session:
        assert session.scalars(select(User)).all() == []


@pytest.mark.parametrize("username", ["ab", "with spaces", "administrador@host", "ação"])
def test_invalid_bootstrap_username_rejected(anonymous_client, isolated_database, username):
    with pytest.raises(auth.BootstrapError, match="Usuário:"):
        auth.bootstrap_admin(isolated_database, username, TEST_PASSWORD)


def test_bootstrap_refuses_existing_viewer(anonymous_client, isolated_database):
    with Session(isolated_database) as session:
        session.add(User(username=TEST_USERNAME, password_hash=auth.hash_password(TEST_PASSWORD), role="viewer"))
        session.commit()
    with pytest.raises(auth.BootstrapError, match="Usuário já existe"):
        auth.bootstrap_admin(isolated_database, TEST_USERNAME, TEST_PASSWORD)


def configure_cli(monkeypatch, engine, passwords):
    monkeypatch.setattr(cli, "engine", engine)
    monkeypatch.setattr(cli.sys, "argv", ["bootstrap_admin"])
    monkeypatch.setattr(cli.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(cli.sys, "stderr", Mock(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda prompt: TEST_USERNAME)
    hidden = Mock(side_effect=passwords)
    monkeypatch.setattr(cli.getpass, "getpass", hidden)
    return hidden


def test_cli_prompts_hidden_and_does_not_print_secrets(anonymous_client, isolated_database, monkeypatch, capsys):
    hidden = configure_cli(monkeypatch, isolated_database, [TEST_PASSWORD, TEST_PASSWORD])
    assert cli.main() == 0
    assert hidden.call_count == 2
    output = capsys.readouterr().out
    assert TEST_PASSWORD not in output and "$argon2" not in output
    with Session(isolated_database) as session:
        assert session.scalar(select(User)).username == TEST_USERNAME


def test_cli_confirmation_mismatch_has_no_effect(anonymous_client, isolated_database, monkeypatch):
    configure_cli(monkeypatch, isolated_database, [TEST_PASSWORD, "different"])
    before = snapshot(isolated_database)
    assert cli.main() == 1
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("failure", ["arguments", "not-tty", "hidden-input"])
def test_cli_refuses_insecure_input(anonymous_client, isolated_database, monkeypatch, failure):
    hidden = configure_cli(monkeypatch, isolated_database, [TEST_PASSWORD, TEST_PASSWORD])
    before = snapshot(isolated_database)
    if failure == "arguments":
        monkeypatch.setattr(cli.sys, "argv", ["bootstrap_admin", TEST_PASSWORD])
    elif failure == "not-tty":
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    else:
        hidden.side_effect = getpass.GetPassWarning("hidden input unavailable")
    assert cli.main() == 1
    assert snapshot(isolated_database) == before
    if failure != "hidden-input":
        hidden.assert_not_called()


def test_login_rotates_and_hashes_tokens(anonymous_client, isolated_database):
    ensure_admin(isolated_database)
    page = anonymous_client.get("/admin/login")
    settings = app.state.auth_settings
    challenge_cookie = anonymous_client.cookies.get(settings.challenge_cookie_name)
    challenge_csrf = csrf_from(page)
    with Session(isolated_database) as session:
        challenge = session.scalar(select(LoginChallenge))
        assert challenge.token_hash == auth.token_hash(challenge_cookie)
        assert challenge.csrf_hash == auth.token_hash(challenge_csrf)
    response = submit_login(anonymous_client, csrf=challenge_csrf)
    assert response.status_code == 303 and response.headers["location"] == "/admin/screens"
    cookie = anonymous_client.cookies.get(settings.session_cookie_name)
    assert cookie != challenge_cookie
    assert len(urlsafe_b64decode(cookie + "=")) == 32
    assert anonymous_client.cookies.get(settings.challenge_cookie_name) is None
    with Session(isolated_database) as session:
        persisted = session.scalar(select(AuthSession))
        assert persisted.token_hash == auth.token_hash(cookie)
        assert persisted.token_hash != cookie
        assert persisted.csrf_token != challenge_csrf
        assert (persisted.expires_at - persisted.created_at).total_seconds() == 28800
        assert session.scalars(select(LoginChallenge)).all() == []
    replay = submit_login(anonymous_client, csrf=challenge_csrf)
    assert replay.status_code == 403


def test_secure_cookie_attributes(anonymous_client, isolated_database):
    ensure_admin(isolated_database)
    page = anonymous_client.get("/admin/login")
    for response in [page, submit_login(anonymous_client, csrf=csrf_from(page))]:
        cookies = response.headers.get_list("set-cookie")
        cookie = next(value for value in cookies if "Max-Age=0" not in value)
        for flag in ("__Host-signage-", "HttpOnly", "SameSite=lax", "Path=/", "Secure"):
            assert flag in cookie
        assert "Domain=" not in cookie
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("case", ["incorrect", "missing-user", "inactive", "viewer"])
def test_login_failure_is_generic(anonymous_client, isolated_database, case, caplog):
    ensure_admin(isolated_database)
    username, password = TEST_USERNAME, TEST_PASSWORD
    if case == "incorrect":
        password = "incorrect"
    elif case == "missing-user":
        username = "missing-user"
    else:
        with Session(isolated_database) as session:
            user = session.scalar(select(User))
            if case == "inactive":
                user.active = False
            else:
                user.role = "viewer"
            session.commit()
    response = submit_login(anonymous_client, username, password)
    assert response.status_code == 401
    assert "Não foi possível entrar. Confira as credenciais ou aguarde para tentar novamente." in response.text
    assert TEST_PASSWORD not in response.text and TEST_PASSWORD not in caplog.text
    assert "$argon2" not in response.text and "$argon2" not in caplog.text
    with Session(isolated_database) as session:
        assert session.scalars(select(AuthSession)).all() == []


def test_nonexistent_user_still_verifies_argon2(anonymous_client, isolated_database, monkeypatch):
    verify = Mock(wraps=auth.verify_password)
    monkeypatch.setattr(auth, "verify_password", verify)
    assert submit_login(anonymous_client, username="missing-user").status_code == 401
    assert verify.call_count == 1
    assert verify.call_args.args[1].startswith("$argon2id$")


@pytest.mark.parametrize("case", ["absent", "missing-field", "invalid", "expired", "another-challenge"])
def test_login_csrf_rejection_never_changes_database(anonymous_client, isolated_database, clock, case):
    page = anonymous_client.get("/admin/login")
    csrf = csrf_from(page)
    if case == "absent":
        csrf = ""
    elif case == "invalid":
        csrf = "x" * 43
    elif case == "expired":
        clock[0] += timedelta(seconds=600)
    elif case == "another-challenge":
        with TestClient(app, base_url="https://testserver") as other:
            csrf = csrf_from(other.get("/admin/login"))
    before = snapshot(isolated_database)
    if case == "missing-field":
        response = anonymous_client.post("/admin/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    else:
        response = submit_login(anonymous_client, csrf=csrf)
    assert response.status_code == 403
    assert snapshot(isolated_database) == before


def test_login_challenge_is_consumed_even_for_wrong_password(anonymous_client, isolated_database):
    ensure_admin(isolated_database)
    page = anonymous_client.get("/admin/login")
    cookie = anonymous_client.cookies.get(app.state.auth_settings.challenge_cookie_name)
    csrf = csrf_from(page)
    assert submit_login(anonymous_client, password="incorrect", csrf=csrf).status_code == 401
    with Session(isolated_database) as session:
        assert session.get(LoginChallenge, auth.token_hash(cookie)) is None


def test_concurrent_challenge_cannot_be_reused(anonymous_client, isolated_database):
    ensure_admin(isolated_database)
    page = anonymous_client.get("/admin/login")
    settings = app.state.auth_settings
    cookie = anonymous_client.cookies.get(settings.challenge_cookie_name)
    csrf = csrf_from(page)
    def attempt(_):
        try:
            auth.login(isolated_database, settings, app.state.auth_clock, cookie, csrf, TEST_USERNAME, TEST_PASSWORD, "test")
            return 303
        except auth.AuthError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, range(2))) == [303, 403]


def test_login_body_errors_do_not_echo_credentials(anonymous_client):
    response = anonymous_client.post("/admin/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 403 and TEST_PASSWORD not in response.text
    oversized = anonymous_client.post("/admin/login", content=b"x" * 8193,
                                       headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert oversized.status_code == 413


def test_account_rate_limit_persists_and_expires(anonymous_client, isolated_database, clock):
    ensure_admin(isolated_database)
    for _ in range(5):
        assert submit_login(anonymous_client, password="incorrect").status_code == 401
    assert submit_login(anonymous_client).status_code == 429
    with TestClient(app, base_url="https://testserver") as restarted:
        assert submit_login(restarted).status_code == 429
    clock[0] += timedelta(seconds=900)
    assert submit_login(anonymous_client).status_code == 303


def test_origin_rate_limit_ignores_spoofed_forwarded_for(anonymous_client, isolated_database):
    app.state.auth_settings = replace(app.state.auth_settings, login_origin_attempts=2)
    for username in ("first-missing", "second-missing"):
        assert submit_login(anonymous_client, username=username).status_code == 401
    page = anonymous_client.get("/admin/login")
    response = anonymous_client.post("/admin/login", data={"username": "third-missing", "password": TEST_PASSWORD,
                                     "csrf_token": csrf_from(page)}, headers={"X-Forwarded-For": "192.0.2.90"})
    assert response.status_code == 429


@pytest.mark.parametrize("path", ["/admin", "/admin/screens", "/admin/screens/new", "/admin/screens/1/edit",
                                  "/admin/media", "/admin/media/new", "/admin/csrf"])
def test_anonymous_admin_get_redirects(anonymous_client, isolated_database, path):
    before = snapshot(isolated_database)
    response = anonymous_client.get(path, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/admin/login"
    assert response.headers["cache-control"] == "no-store"
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("method,path", [("GET", "/api/screens"), ("GET", "/api/screens/1"),
                                         ("POST", "/api/screens"), ("PATCH", "/api/screens/1"),
                                         ("GET", "/media/1/file")])
def test_anonymous_api_and_media_are_401_json(anonymous_client, isolated_database, method, path):
    before = snapshot(isolated_database)
    response = anonymous_client.request(method, path, content=b"invalid body", headers={"Range": "bytes=0-99"})
    assert response.status_code == 401 and response.json()["detail"] == "Autenticação necessária."
    assert response.headers["cache-control"] == "no-store"
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("path", ["/admin/screens", "/admin/screens/1/edit", "/admin/screens/1/toggle", "/admin/media", "/admin/logout"])
def test_anonymous_post_has_no_effect(anonymous_client, isolated_database, isolated_media, path):
    before = snapshot(isolated_database)
    response = anonymous_client.post(path, data=SCREEN, files={"file": ("real.mp4", b"upload")}, follow_redirects=False)
    assert response.status_code == 401
    assert snapshot(isolated_database) == before
    assert list(isolated_media.directory.iterdir()) == []


@pytest.mark.parametrize("case", ["revoked", "inactive", "unknown-token", "malformed-token"])
def test_session_cannot_authenticate(client, isolated_database, case):
    settings = app.state.auth_settings
    with Session(isolated_database) as session:
        if case == "revoked":
            session.scalar(select(AuthSession)).revoked = True
        elif case == "inactive":
            session.scalar(select(User)).active = False
        session.commit()
    if case in {"unknown-token", "malformed-token"}:
        client.cookies.clear()
        client.cookies.set(settings.session_cookie_name, "x" * 43 if case == "unknown-token" else "invalid")
    before = snapshot(isolated_database)
    assert client.get("/api/screens").status_code == 401
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("method,path", [("GET", "/admin/screens"), ("GET", "/admin/media"),
                                         ("GET", "/api/screens"), ("GET", "/api/screens/1"),
                                         ("GET", "/media/1/file"), ("POST", "/admin/screens"),
                                         ("POST", "/admin/media"), ("POST", "/api/screens"),
                                         ("PATCH", "/api/screens/1"), ("GET", "/admin/csrf")])
def test_viewer_cannot_access(client, isolated_database, isolated_media, clock, method, path):
    with Session(isolated_database) as session:
        session.scalar(select(User)).role = "viewer"
        session.commit()
    # Mesmo quando uma atualização de atividade seria devida, a negação não escreve.
    clock[0] += timedelta(seconds=600)
    before = snapshot(isolated_database)
    response = client.request(method, path, data=SCREEN)
    assert response.status_code == 403
    assert snapshot(isolated_database) == before
    assert list(isolated_media.directory.iterdir()) == []


@pytest.mark.parametrize("path", ["/admin/screens", "/admin/screens/1/edit", "/admin/screens/1/toggle", "/admin/media", "/admin/logout"])
@pytest.mark.parametrize("csrf", [None, "wrong", "x" * 43])
def test_admin_csrf_rejection_does_not_modify_data(client, isolated_database, isolated_media, path, csrf):
    client.post("/api/screens", json=SCREEN)
    before = snapshot(isolated_database)
    data = {**SCREEN, "title": "Campanha"}
    if csrf is not None:
        data["csrf_token"] = csrf
    response = TestClient.request(client, "POST", path, data=data, files={"file": ("campaign.png", b"upload")})
    assert response.status_code == 403
    assert snapshot(isolated_database) == before
    assert list(isolated_media.directory.iterdir()) == []


@pytest.mark.parametrize("method,path,payload", [("POST", "/api/screens", SCREEN), ("PATCH", "/api/screens/1", {"active": False})])
@pytest.mark.parametrize("csrf", [None, "wrong", "x" * 43])
def test_api_csrf_rejection_is_json_without_mutation(client, isolated_database, method, path, payload, csrf):
    client.post("/api/screens", json=SCREEN)
    before = snapshot(isolated_database)
    headers = {} if csrf is None else {"X-CSRF-Token": csrf}
    response = TestClient.request(client, method, path, json=payload, headers=headers)
    assert response.status_code == 403 and "detail" in response.json()
    assert snapshot(isolated_database) == before


def test_csrf_from_another_session_rejected(client, isolated_database):
    with TestClient(app, base_url="https://testserver") as other:
        assert submit_login(other).status_code == 303
        another_csrf = other.get("/admin/csrf").json()["csrf_token"]
    before = snapshot(isolated_database)
    response = client.post("/api/screens", json=SCREEN, headers={"X-CSRF-Token": another_csrf})
    assert response.status_code == 403
    assert snapshot(isolated_database) == before


def test_all_forms_have_session_csrf(client):
    screen = client.post("/api/screens", json=SCREEN).json()
    for path in ("/admin/screens", "/admin/screens/new", f"/admin/screens/{screen['id']}/edit", "/admin/media/new"):
        page = client.get(path)
        tokens = CsrfInput(page.text).tokens
        assert tokens and set(tokens) == {client.csrf_token}
        assert 'action="https://testserver/admin/logout"' in page.text
        assert TEST_USERNAME in page.text
    response = client.get("/admin/csrf")
    assert response.json() == {"csrf_token": client.csrf_token}
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in response.headers


def test_logout_revokes_copied_cookie(client, isolated_database):
    copied = client.cookies.get(app.state.auth_settings.session_cookie_name)
    response = client.post("/admin/logout", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/admin/login"
    assert client.cookies.get(app.state.auth_settings.session_cookie_name) is None
    with Session(isolated_database) as session:
        assert session.scalar(select(AuthSession)).revoked
    with TestClient(app, base_url="https://testserver") as attacker:
        attacker.cookies.set(app.state.auth_settings.session_cookie_name, copied)
        assert attacker.get("/api/screens").status_code == 401


def test_get_cannot_logout(client, isolated_database):
    before = snapshot(isolated_database)
    assert client.get("/admin/logout").status_code == 405
    assert snapshot(isolated_database) == before


@pytest.mark.parametrize("kind", ["idle", "absolute"])
def test_session_timeout_is_server_enforced(client, isolated_database, clock, kind):
    with Session(isolated_database) as session:
        record = session.scalar(select(AuthSession))
        now = auth.timestamp(app.state.auth_clock)
        record.created_at = now
        record.last_activity_at = now
        record.expires_at = now + timedelta(seconds=1800 if kind == "absolute" else 28800)
        session.commit()
    clock[0] += timedelta(seconds=1800)
    if kind == "absolute":
        with Session(isolated_database) as session:
            session.scalar(select(AuthSession)).last_activity_at = auth.timestamp(app.state.auth_clock)
            session.commit()
    before = snapshot(isolated_database)
    assert client.get("/api/screens").status_code == 401
    assert snapshot(isolated_database) == before


def test_reads_do_not_write_and_successful_mutations_touch_session(client, isolated_database, clock):
    stored = client.post("/api/screens", json=SCREEN).json()
    with Session(isolated_database) as session:
        original = session.scalar(select(AuthSession))
        last, expiration = original.last_activity_at, original.expires_at
    clock[0] += timedelta(seconds=299)
    client.get("/api/screens")
    assert client.patch(f"/api/screens/{stored['id']}", json={"name": "TV Piloto nova"}).status_code == 200
    with Session(isolated_database) as session:
        assert session.scalar(select(AuthSession)).last_activity_at == last
    clock[0] += timedelta(seconds=1)
    before = snapshot(isolated_database)
    for path in ("/api/screens", "/admin/screens", "/admin/media", "/admin/csrf"):
        assert client.get(path).status_code == 200
    assert snapshot(isolated_database) == before
    assert client.patch(f"/api/screens/{stored['id']}", json={"active": False}).status_code == 200
    with Session(isolated_database) as session:
        current = session.scalar(select(AuthSession))
        assert current.last_activity_at == last + timedelta(seconds=300)
        assert current.expires_at == expiration


def test_denied_csrf_never_touches_activity(client, isolated_database, clock):
    clock[0] += timedelta(seconds=300)
    before = snapshot(isolated_database)
    response = TestClient.request(client, "POST", "/api/screens", json=SCREEN)
    assert response.status_code == 403
    assert snapshot(isolated_database) == before


def test_session_and_user_survive_application_restart(client, isolated_database):
    cookies = dict(client.cookies)
    isolated_database.dispose()
    with TestClient(app, base_url="https://testserver") as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get("/api/screens").status_code == 200
        assert restarted.get("/admin/csrf").json()["csrf_token"] == client.csrf_token


def test_tokens_in_query_do_not_authenticate(client, anonymous_client):
    cookie = client.cookies.get(app.state.auth_settings.session_cookie_name)
    assert anonymous_client.get("/api/screens", params={"session": cookie, "csrf_token": client.csrf_token}).status_code == 401


@pytest.mark.parametrize("path", ["/", "/health", "/static/admin.css"])
def test_health_and_login_css_remain_public(anonymous_client, path):
    assert anonymous_client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_documentation_is_disabled(anonymous_client, path):
    assert anonymous_client.get(path).status_code == 404


def test_http_lan_never_emits_login_cookie(anonymous_client, isolated_database):
    before = snapshot(isolated_database)
    for path in ("/admin/login", "/admin", "/api/screens", "/media/1/file"):
        response = anonymous_client.get("http://10.4.254.202:8080" + path,
                                         headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"})
        assert response.status_code == 503 and "set-cookie" not in response.headers
    assert snapshot(isolated_database) == before
    assert anonymous_client.get("http://10.4.254.202:8080/health").status_code == 200


def test_explicit_local_test_cookie(monkeypatch, isolated_database):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("LOCAL_AUTH_TEST_MODE", "true")
    with TestClient(app, base_url="http://127.0.0.1:18080") as local:
        ensure_admin(isolated_database)
        response = submit_login(local)
        assert response.status_code == 303
        cookie = next(value for value in response.headers.get_list("set-cookie") if "Max-Age=0" not in value)
        assert "signage-local-session" in cookie and "Secure" not in cookie
        for flag in ("HttpOnly", "SameSite=lax", "Path=/"):
            assert flag in cookie
        assert local.get("/api/screens").status_code == 200
        assert local.get("http://10.4.254.202:8080/admin/login").status_code == 503


@pytest.mark.parametrize("changes", [
    {"session_cookie_secure": False},
    {"session_cookie_secure": False, "local_auth_test_mode": True, "bind_ip": "10.4.254.202"},
    {"session_cookie_secure": False, "local_auth_test_mode": True, "bind_ip": "0.0.0.0"},
    {"session_cookie_secure": False, "local_auth_test_mode": True, "port": 9090},
    {"local_auth_test_mode": True},
    {"session_cookie_secure": False, "local_auth_test_mode": True, "forwarded_allow_ips": "127.0.0.1"},
    {"forwarded_allow_ips": "*"}, {"session_idle_seconds": 0},
    {"session_touch_seconds": 1800}, {"session_absolute_seconds": 60},
])
def test_unsafe_or_contradictory_config_is_rejected(changes):
    with pytest.raises(ValueError):
        AuthSettings(**changes)


def test_invalid_bool_and_startup_fail_before_database(monkeypatch, isolated_database):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    assert not inspect(isolated_database).has_table("screens")
    with pytest.raises(ValueError, match="Secure=false"):
        with TestClient(app):
            pass
    assert not inspect(isolated_database).has_table("screens")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "invalid")
    with pytest.raises(ValueError, match="true ou false"):
        get_auth_settings()


def test_security_headers_preserve_previews(client):
    response = client.get("/admin/media")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "media-src 'self'" in response.headers["content-security-policy"]
    assert "form-action 'self'" in response.headers["content-security-policy"]


def test_existing_schema_and_records_survive_auth_tables(isolated_database):
    Screen.__table__.create(isolated_database)
    MediaAsset.__table__.create(isolated_database)
    with Session(isolated_database) as session:
        session.add(Screen(**SCREEN))
        session.add(MediaAsset(title="Anterior", kind="image", original_filename="original.png",
                               stored_filename="12345678-1234-4234-8234-123456789012.png", mime_type="image/png",
                               size_bytes=1, width=1, height=1, frame_count=1))
        session.commit()
    with isolated_database.connect() as connection:
        before = [connection.execute(model.__table__.select()).all() for model in (Screen, MediaAsset)]
    for _ in range(2):
        Base.metadata.create_all(isolated_database)
    with isolated_database.connect() as connection:
        after = [connection.execute(model.__table__.select()).all() for model in (Screen, MediaAsset)]
    assert after == before
    assert set(inspect(isolated_database).get_table_names()) == {
        "screens", "media_assets", "users", "auth_sessions", "login_challenges", "login_limits",
        "playlists", "playlist_items", "screen_playlist_assignments",
        "screen_pairing_codes", "screen_device_sessions", "device_activation_challenges", "device_activation_limits"}
