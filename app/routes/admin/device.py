from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_session
from app.models import ScreenDeviceSession
from app.routes.admin.screens import templates
from app.security import require_form_csrf
from app.services import auth, device_auth

router = APIRouter(prefix="/admin/screens", dependencies=[Depends(require_form_csrf)])


def page(request, screen_id, session, code=None):
    screen = device_auth.screen_for_admin(session, screen_id)
    device = session.get(ScreenDeviceSession, screen.id)
    expiration = device.expires_at if device and device.expires_at > auth.timestamp(request.app.state.auth_clock) else None
    return templates.TemplateResponse(request=request, name="admin/screens/player.html",
                                      context={"screen": screen, "expiration": expiration, "code": code})


@router.get("/{screen_id}/player", name="admin_screen_player")
def status(request: Request, screen_id: str, session: Session = Depends(get_session)):
    return page(request, screen_id, session)


@router.post("/{screen_id}/player/pairing", name="admin_screen_pairing")
def pairing(request: Request, screen_id: str, session: Session = Depends(get_session)):
    code = device_auth.issue_code(request.app.state.engine, request.app.state.auth_clock,
                                  screen_id, request.state.auth.user_id)
    # 200 intencional: segredo aparece só nesta resposta POST, nunca em GET/URL.
    return page(request, screen_id, session, code=code)


@router.post("/{screen_id}/player/revoke", name="admin_screen_revoke")
async def revoke(request: Request, screen_id: str):
    fields = await request.form()
    if fields.getlist("confirm") != ["revoke"]:
        raise auth.AuthError(422, "Confirme a revogação do dispositivo e do código pendente.")
    await run_in_threadpool(device_auth.revoke, request.app.state.engine, screen_id)
    return RedirectResponse(request.url_for("admin_screen_player", screen_id=screen_id), status_code=303)
