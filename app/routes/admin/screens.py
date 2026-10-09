from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import ScreenCreate, ScreenUpdate
from app.services import screens

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")
slug_pattern = ScreenCreate.model_json_schema()["properties"]["slug"]["pattern"]
notices = {
    "created": "Tela cadastrada com sucesso.",
    "updated": "Tela atualizada com sucesso.",
    "activated": "Tela ativada com sucesso.",
    "deactivated": "Tela desativada com sucesso.",
}


def render_form(request, values, screen_id=None, errors=None, status_code=200):
    return templates.TemplateResponse(
        request=request,
        name="admin/screens/form.html",
        context={
            "values": values,
            "screen_id": screen_id,
            "errors": errors or {},
            "slug_pattern": slug_pattern,
        },
        status_code=status_code,
    )


def not_found(request):
    return templates.TemplateResponse(
        request=request, name="admin/screens/not_found.html", status_code=404
    )


def redirect_to_list(request, result):
    url = request.url_for("admin_screens").include_query_params(result=result)
    return RedirectResponse(url, status_code=303)


def submit_form(request, values, session, screen=None):
    screen_id = screen.id if screen is not None else None
    schema = ScreenUpdate if screen is not None else ScreenCreate
    try:
        data = schema(**values)
    except ValidationError as exc:
        messages = {
            "string_too_short": "Preencha este campo.",
            "string_too_long": "Use no máximo 200 caracteres.",
            "string_pattern_mismatch": (
                "Use letras minúsculas sem acentos, números e hífens entre palavras."
            ),
        }
        errors = {
            error["loc"][0]: messages.get(error["type"], "Confira o valor deste campo.")
            for error in exc.errors()
        }
        return render_form(request, values, screen_id, errors, status_code=422)

    try:
        if screen is None:
            screens.create_screen(data, session)
        else:
            screens.update_screen(screen, data, session)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        return render_form(
            request, values, screen_id,
            {"slug": "Já existe uma tela com esse slug."}, status_code=409,
        )
    return redirect_to_list(request, "updated" if screen is not None else "created")


@router.get("")
def admin_index(request: Request):
    return RedirectResponse(request.url_for("admin_screens"), status_code=303)


@router.get("/screens", response_class=HTMLResponse, name="admin_screens")
def list_screens(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        request=request,
        name="admin/screens/list.html",
        context={
            "screens": screens.list_screens(session),
            "notice": notices.get(request.query_params.get("result")),
        },
    )


@router.get("/screens/new", response_class=HTMLResponse, name="admin_new_screen")
def new_screen(request: Request):
    return render_form(request, {"name": "", "slug": "", "location": ""})


@router.post("/screens", response_class=HTMLResponse, name="admin_create_screen")
def create_screen(
    request: Request,
    name: str = Form(default=""),
    slug: str = Form(default=""),
    location: str = Form(default=""),
    session: Session = Depends(get_session),
):
    return submit_form(request, {"name": name, "slug": slug, "location": location}, session)


@router.get("/screens/{screen_id}/edit", response_class=HTMLResponse, name="admin_edit_screen")
def edit_screen(request: Request, screen_id: int, session: Session = Depends(get_session)):
    try:
        screen = screens.find_screen(screen_id, session)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return not_found(request)
    return render_form(
        request,
        {"name": screen.name, "slug": screen.slug, "location": screen.location},
        screen.id,
    )


@router.post("/screens/{screen_id}/edit", response_class=HTMLResponse, name="admin_update_screen")
def update_screen(
    request: Request,
    screen_id: int,
    name: str = Form(default=""),
    slug: str = Form(default=""),
    location: str = Form(default=""),
    session: Session = Depends(get_session),
):
    try:
        screen = screens.find_screen(screen_id, session)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return not_found(request)
    return submit_form(
        request, {"name": name, "slug": slug, "location": location}, session, screen
    )


@router.post("/screens/{screen_id}/toggle", response_class=HTMLResponse, name="admin_toggle_screen")
def toggle_screen(request: Request, screen_id: int, session: Session = Depends(get_session)):
    try:
        screen = screens.find_screen(screen_id, session)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return not_found(request)
    screen = screens.update_screen(screen, ScreenUpdate(active=not screen.active), session)
    return redirect_to_list(request, "activated" if screen.active else "deactivated")
