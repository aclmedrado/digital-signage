from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest

DATA = {"name": "TV Recepção", "slug": "recepcao", "location": "Recepção"}


class Inputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input":
            self.fields[attrs["name"]] = attrs


def assert_html(response, status_code=200):
    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("text/html")


def assert_list_redirect(response):
    assert response.status_code == 303
    assert urlsplit(response.headers["location"]).path == "/admin/screens"


def create_api(client, **changes):
    response = client.post("/api/screens", json={**DATA, **changes})
    assert response.status_code == 201
    return response.json()


def test_admin_redirect(client):
    response = client.get("/admin", follow_redirects=False)
    assert_list_redirect(response)
    assert urlsplit(response.headers["location"]).query == ""


def test_empty_list(client):
    response = client.get("/admin/screens")
    assert_html(response)
    assert "Nenhuma tela cadastrada" in response.text
    assert "Nova tela" in response.text


@pytest.mark.parametrize("active", [True, False])
def test_list(client, active):
    first = create_api(client, active=active)
    second = create_api(client, name="TV Segunda", slug="segunda")
    response = client.get("/admin/screens")
    assert_html(response)
    for value in DATA.values():
        assert value in response.text
    assert ("Ativa" if active else "Inativa") in response.text
    assert ("Desativar" if active else "Ativar") in response.text
    assert f"/admin/screens/{first['id']}/edit" in response.text
    assert f"/admin/screens/{first['id']}/toggle" in response.text
    assert 'method="post"' in response.text
    assert response.text.index(first["name"]) < response.text.index(second["name"])


def test_new_form(client):
    response = client.get("/admin/screens/new")
    assert_html(response)
    fields = Inputs(response.text).fields
    assert set(fields) == set(DATA)
    for field in fields.values():
        assert field["value"] == ""
        assert "required" in field
        assert field["maxlength"] == "200"
    assert fields["slug"]["pattern"] == r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    for name in DATA:
        assert f'<label for="{name}">' in response.text


def test_create(client):
    # O estado inicial continua ativo, mesmo com um campo extra na requisição.
    response = client.post("/admin/screens", data={**DATA, "active": "false"}, follow_redirects=False)
    assert_list_redirect(response)
    page = client.get(response.headers["location"])
    assert_html(page)
    assert DATA["name"] in page.text
    assert "Tela cadastrada com sucesso." in page.text
    stored = client.get("/api/screens").json()
    assert len(stored) == 1
    assert {key: stored[0][key] for key in DATA} == DATA
    assert stored[0]["active"] is True
    # Atualizar a página de destino faz somente GET, sem novo cadastro.
    assert_html(client.get(response.headers["location"]))
    assert client.get("/api/screens").json() == stored


def test_duplicate_create(client):
    existing = create_api(client)
    values = {**DATA, "name": "TV Duplicada", "location": "Outro local"}
    response = client.post("/admin/screens", data=values)
    assert_html(response, 409)
    assert "Já existe uma tela com esse slug." in response.text
    assert {name: field["value"] for name, field in Inputs(response.text).fields.items()} == values
    assert client.get("/api/screens").json() == [existing]


def test_edit_form(client):
    screen = create_api(client)
    response = client.get(f"/admin/screens/{screen['id']}/edit")
    assert_html(response)
    fields = Inputs(response.text).fields
    assert set(fields) == set(DATA)
    assert {name: field["value"] for name, field in fields.items()} == DATA
    assert f"/admin/screens/{screen['id']}/edit" in response.text


@pytest.mark.parametrize("active", [True, False])
def test_edit(client, active):
    screen = create_api(client, active=active)
    values = {"name": "TV Nova", "slug": "tv-nova", "location": "Novo local"}
    response = client.post(
        f"/admin/screens/{screen['id']}/edit",
        data={**values, "active": str(not active).lower()},
        follow_redirects=False,
    )
    assert_list_redirect(response)
    updated = client.get(f"/api/screens/{screen['id']}").json()
    assert {key: updated[key] for key in values} == values
    assert updated["active"] is active
    assert updated["created_at"] == screen["created_at"]
    assert updated["updated_at"] > screen["updated_at"]
    page = client.get(response.headers["location"])
    assert_html(page)
    assert values["name"] in page.text
    assert "Tela atualizada com sucesso." in page.text


def test_duplicate_edit_rolls_back_all_fields(client):
    first = create_api(client)
    second = create_api(client, slug="segunda")
    values = {"name": "Nome alterado", "slug": first["slug"], "location": "Outro local"}
    response = client.post(f"/admin/screens/{second['id']}/edit", data=values)
    assert_html(response, 409)
    assert "Já existe uma tela com esse slug." in response.text
    assert {name: field["value"] for name, field in Inputs(response.text).fields.items()} == values
    assert client.get("/api/screens").json() == [first, second]


@pytest.mark.parametrize("method,path", [("get", "edit"), ("post", "edit"), ("post", "toggle")])
def test_missing_screen(client, method, path):
    response = getattr(client, method)(f"/admin/screens/999999/{path}")
    assert_html(response, 404)
    assert "Tela não encontrada" in response.text
    assert client.get("/api/screens").json() == []


def test_toggle(client):
    original = create_api(client)
    url = f"/admin/screens/{original['id']}/toggle"
    previous = original
    for active, label, notice in [
        (False, "Ativar", "Tela desativada com sucesso."),
        (True, "Desativar", "Tela ativada com sucesso."),
    ]:
        response = client.post(url, follow_redirects=False)
        assert_list_redirect(response)
        stored = client.get(f"/api/screens/{original['id']}").json()
        assert stored["active"] is active
        assert stored["updated_at"] > previous["updated_at"]
        for field in ("id", "name", "slug", "location", "created_at"):
            assert stored[field] == original[field]
        page = client.get(response.headers["location"])
        assert_html(page)
        assert label in page.text
        assert notice in page.text
        previous = stored


@pytest.mark.parametrize("active", [True, False])
def test_get_cannot_toggle(client, active):
    original = create_api(client, active=active)
    response = client.get(f"/admin/screens/{original['id']}/toggle")
    assert response.status_code == 405
    assert client.get(f"/api/screens/{original['id']}").json() == original


@pytest.mark.parametrize("suffix", ["", "/edit", "/toggle"])
def test_no_admin_delete(client, suffix):
    original = create_api(client)
    response = client.delete(f"/admin/screens/{original['id']}{suffix}")
    assert response.status_code in (404, 405)
    assert client.get(f"/api/screens/{original['id']}").json() == original


@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize("field,value,message", [
    ("name", "", "Preencha este campo."),
    ("slug", "", "Preencha este campo."),
    ("location", "", "Preencha este campo."),
    ("name", "x" * 201, "Use no máximo 200 caracteres."),
    ("slug", "x" * 201, "Use no máximo 200 caracteres."),
    ("location", "x" * 201, "Use no máximo 200 caracteres."),
    ("slug", "TV_Recepção", "Use letras minúsculas sem acentos"),
])
def test_invalid_form_is_html_and_preserves_values(client, editing, field, value, message):
    original = create_api(client) if editing else None
    url = f"/admin/screens/{original['id']}/edit" if editing else "/admin/screens"
    values = {**DATA, field: value}
    response = client.post(url, data=values)
    assert_html(response, 422)
    assert message in response.text
    fields = Inputs(response.text).fields
    assert {name: attrs["value"] for name, attrs in fields.items()} == values
    assert fields[field]["aria-invalid"] == "true"
    assert client.get("/api/screens").json() == ([original] if editing else [])


@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize("field", ["name", "slug", "location"])
def test_missing_form_field_is_html(client, editing, field):
    original = create_api(client) if editing else None
    url = f"/admin/screens/{original['id']}/edit" if editing else "/admin/screens"
    values = {name: value for name, value in DATA.items() if name != field}
    response = client.post(url, data=values)
    assert_html(response, 422)
    assert "Preencha este campo." in response.text
    assert Inputs(response.text).fields[field]["value"] == ""
    assert client.get("/api/screens").json() == ([original] if editing else [])


def test_edit_unchanged_values_updates_timestamp(client):
    original = create_api(client)
    response = client.post(f"/admin/screens/{original['id']}/edit", data=DATA, follow_redirects=False)
    assert_list_redirect(response)
    stored = client.get(f"/api/screens/{original['id']}").json()
    assert stored["updated_at"] > original["updated_at"]


def test_html_escapes_screen_values(client):
    payload = '<script>alert("teste")</script>'
    values = {**DATA, "name": payload, "location": payload}
    original = create_api(client, **values)
    listing = client.get("/admin/screens")
    edit = client.get(f"/admin/screens/{original['id']}/edit")
    error = client.post("/admin/screens", data=values)
    for response in (listing, edit, error):
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text
    for response in (edit, error):
        assert Inputs(response.text).fields["name"]["value"] == payload
        assert Inputs(response.text).fields["location"]["value"] == payload


def test_local_stylesheet(client):
    page = client.get("/admin/screens")
    assert "/static/admin.css" in page.text
    response = client.get("/static/admin.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
