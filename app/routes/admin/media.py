from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import MediaSettings, get_media_settings
from app.database import get_session
from app.security import require_form_csrf
from app.services import media

router = APIRouter(prefix="/admin/media", dependencies=[Depends(require_form_csrf)])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")


def render_form(request, title="", error=None, status_code=200, settings=None):
    return templates.TemplateResponse(
        request=request, name="admin/media/form.html",
        context={"title": title, "error": error, "settings": settings or get_media_settings()},
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse, name="admin_media")
def list_media(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        request=request, name="admin/media/list.html",
        context={"assets": media.list_media(session),
                 "notice": "Mídia cadastrada com sucesso." if request.query_params.get("result") == "created" else None},
    )


@router.get("/new", response_class=HTMLResponse, name="admin_new_media")
def new_media(request: Request, settings: MediaSettings = Depends(get_media_settings)):
    return render_form(request, settings=settings)


@router.post("", response_class=HTMLResponse, name="admin_create_media")
def create_media(request: Request, title: str = Form(default=""),
                 file: UploadFile | None = File(default=None),
                 session: Session = Depends(get_session),
                 settings: MediaSettings = Depends(get_media_settings)):
    try:
        media.create_media(title, file, session, settings)
    except media.MediaError as exc:
        return render_form(request, title, str(exc), exc.status_code, settings)
    url = request.url_for("admin_media").include_query_params(result="created")
    return RedirectResponse(url, status_code=303)
