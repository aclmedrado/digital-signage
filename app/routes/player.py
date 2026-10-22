from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import MediaSettings, get_media_settings
from app.database import get_session
from app.routes.media import asset_response
from app.security import PLAYER_CSP
from app.services import auth, device_auth, player

router = APIRouter(prefix="/player/s")
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/{slug}", name="player_page")
def index(request: Request, slug: str, session: Session = Depends(get_session)):
    try:
        screen = device_auth.authenticated_screen(request, session, slug)
    except auth.AuthError as exc:
        if exc.status_code == 401:
            return RedirectResponse("/device/activate", status_code=303)
        raise
    return templates.TemplateResponse(request=request, name="player/index.html",
                                      context={"slug": screen.slug},
                                      headers={"Content-Security-Policy": PLAYER_CSP})


@router.get("/{slug}/manifest", name="player_manifest")
def manifest(request: Request, slug: str, session: Session = Depends(get_session)):
    screen = device_auth.authenticated_screen(request, session, slug)
    return player.manifest(screen.id, session)


@router.get("/{slug}/media/{media_id}", name="player_media")
def media(request: Request, slug: str, media_id: str, session: Session = Depends(get_session),
          settings: MediaSettings = Depends(get_media_settings)):
    screen = device_auth.authenticated_screen(request, session, slug)
    asset = player.current_asset(screen.id, media_id, session)
    return asset_response(asset, settings)
