from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.security import clear_cookie, denied, set_cookie
from app.services import auth, device_auth

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


async def activation_form(request, error=None, status_code=200):
    settings = request.app.state.auth_settings
    cookie, csrf = await run_in_threadpool(device_auth.create_challenge, request.app.state.engine,
                                          request.app.state.auth_clock,
                                          request.cookies.get(settings.activation_cookie_name))
    response = templates.TemplateResponse(request=request, name="player/activate.html",
                                           context={"csrf": csrf, "error": error}, status_code=status_code)
    set_cookie(response, settings.activation_cookie_name, cookie, settings, device_auth.CHALLENGE_SECONDS)
    return response


@router.get("/device/activate", name="device_activate")
async def activate_page(request: Request):
    return await activation_form(request)


@router.post("/device/activate", name="device_submit_activation")
async def activate(request: Request):
    # Não usar Form/Pydantic para evitar reflexão do segredo em erros 422.
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            raise ValueError()
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 2048:
                return denied(request, 413, "Formulário excede o limite permitido.")
            body.extend(chunk)
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True, max_num_fields=2)
        if set(fields) != {"code", "csrf_token"} or any(len(values) != 1 for values in fields.values()):
            raise ValueError()
    except ValueError:
        return denied(request, 403, "Formulário expirado ou inválido. Abra novamente a ativação.")
    settings = request.app.state.auth_settings
    try:
        cookie, slug = await run_in_threadpool(device_auth.activate, request.app.state.engine,
                                               request.app.state.auth_clock,
                                               request.cookies.get(settings.activation_cookie_name),
                                               fields["csrf_token"][0], fields["code"][0],
                                               request.client.host if request.client else "unknown")
    except auth.AuthError as exc:
        if exc.status_code in {401, 429}:
            response = await activation_form(request, str(exc), exc.status_code)
            if exc.status_code == 429:
                response.headers["Retry-After"] = str(device_auth.WINDOW_SECONDS)
            return response
        raise
    response = RedirectResponse(f"/player/s/{slug}", status_code=303)
    clear_cookie(response, settings.activation_cookie_name, settings)
    set_cookie(response, settings.device_cookie_name, cookie, settings, device_auth.DEVICE_SECONDS)
    return response
