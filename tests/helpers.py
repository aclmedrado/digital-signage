"""Clientes de regressão usam login real; não fazem bypass de autorização."""
from html.parser import HTMLParser

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.auth import bootstrap_admin

TEST_USERNAME = "admin-test"
TEST_PASSWORD = "Fixture-006-Password!"


class CsrfInput(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tokens = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "csrf_token":
            self.tokens.append(attributes["value"])


def csrf_from(response):
    return CsrfInput(response.text).tokens[0]


def ensure_admin(engine):
    with Session(engine) as session:
        exists = session.scalar(select(User.id).where(User.username == TEST_USERNAME))
    if exists is None:
        bootstrap_admin(engine, TEST_USERNAME, TEST_PASSWORD)


class AuthenticatedClient(TestClient):
    csrf_token = None

    def __init__(self, app):
        super().__init__(app, base_url="https://testserver")

    def authenticate(self, engine):
        ensure_admin(engine)
        login = self.get("/admin/login")
        response = self.post("/admin/login", data={"username": TEST_USERNAME,
                              "password": TEST_PASSWORD, "csrf_token": csrf_from(login)}, follow_redirects=False)
        assert response.status_code == 303
        self.csrf_token = self.get("/admin/csrf").json()["csrf_token"]

    def request(self, method, url, **kwargs):
        path = str(url)
        if self.csrf_token and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            if "/api/screens" in path:
                kwargs["headers"] = {"X-CSRF-Token": self.csrf_token, **(kwargs.get("headers") or {})}
            elif "/admin/" in path and "/admin/login" not in path:
                kwargs["data"] = {"csrf_token": self.csrf_token, **(kwargs.get("data") or {})}
        return super().request(method, url, **kwargs)
