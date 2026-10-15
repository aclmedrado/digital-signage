from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.security import clear_cookie, denied, require_form_csrf, set_cookie
from app.services import auth

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")


async def login_form(request, error=None, status_code=200):
    settings = request.app.state.auth_settings
    cookie, csrf = await run_in_threadpool(auth.create_challenge, request.app.state.engine, settings,
                                          request.app.state.auth_clock, request.cookies.get(settings.challenge_cookie_name))
    response = templates.TemplateResponse(request=request, name="admin/auth/login.html",
                                           context={"login_csrf": csrf, "error": error}, status_code=status_code)
    set_cookie(response, settings.challenge_cookie_name, cookie, settings, settings.login_challenge_seconds)
    return response


@router.get("/login", name="admin_login")
async def show_login(request: Request):
    return await login_form(request)


@router.post("/login", name="admin_submit_login")
async def submit_login(request: Request):
    # Sem parâmetros Form/Pydantic: erros nunca devolvem senha/corpo ao cliente.
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            raise ValueError()
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 8192:
                return denied(request, 413, "Formulário de login excede o limite permitido.")
            body.extend(chunk)
        form = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True, max_num_fields=3)
        if set(form) != {"username", "password", "csrf_token"} or any(len(value) != 1 for value in form.values()):
            raise ValueError()
        username, password, csrf = (form[name][0] for name in ("username", "password", "csrf_token"))
    except ValueError:
        return denied(request, 403, "Formulário expirado ou inválido. Abra novamente o login.")
    settings = request.app.state.auth_settings
    try:
        cookie = await run_in_threadpool(auth.login, request.app.state.engine, settings,
                                         request.app.state.auth_clock,
                                         request.cookies.get(settings.challenge_cookie_name),
                                         csrf, username, password,
                                         request.client.host if request.client else "unknown")
    except auth.AuthError as exc:
        if exc.status_code == 403:
            return denied(request, 403, str(exc))
        return await login_form(request, str(exc), exc.status_code)
    response = RedirectResponse("/admin/screens", status_code=303)
    clear_cookie(response, settings.challenge_cookie_name, settings)
    set_cookie(response, settings.session_cookie_name, cookie, settings, settings.session_absolute_seconds)
    return response


@router.post("/logout", name="admin_logout", dependencies=[Depends(require_form_csrf)])
async def logout(request: Request):
    await run_in_threadpool(auth.logout, request.app.state.engine, request.state.auth)
    response = RedirectResponse("/admin/login", status_code=303)
    settings = request.app.state.auth_settings
    clear_cookie(response, settings.session_cookie_name, settings)
    clear_cookie(response, settings.challenge_cookie_name, settings)
    return response


@router.get("/csrf", name="admin_csrf")
def csrf_token(request: Request):
    # Somente sessão admin autorizada pelo middleware; nunca em URL/cache público.
    return JSONResponse({"csrf_token": request.state.auth.csrf_token})
