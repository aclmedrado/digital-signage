"""Proteção antes da leitura do corpo; CSRF HTML é conferido pelas dependências."""
from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from app.services import auth

HTML_CSP = "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self'; media-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
PLAYER_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def transport_allowed(request, settings):
    if settings.session_cookie_secure:
        return request.url.scheme == "https"
    return settings.local_auth_test_mode and settings.bind_ip == "127.0.0.1" and settings.port == 8080 and request.url.scheme == "http" and request.url.hostname in {"127.0.0.1", "localhost"}


def set_cookie(response, name, value, settings, max_age):
    response.set_cookie(name, value, max_age=max_age, secure=settings.session_cookie_secure,
                        httponly=True, samesite="lax", path="/")


def clear_cookie(response, name, settings):
    response.delete_cookie(name, secure=settings.session_cookie_secure, httponly=True,
                           samesite="lax", path="/")


def denied(request, code, message):
    if request.url.path.startswith("/admin"):
        response = HTMLResponse(f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Acesso restrito</title><h1>{message}</h1><a href='/admin/login'>Entrar</a></html>", status_code=code)
    else:
        response = JSONResponse({"detail": message}, status_code=code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = HTML_CSP
    return response


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = StarletteRequest(scope, receive)
        path = scope["path"]
        protected = path == "/admin" or path.startswith(("/admin/", "/api/screens", "/media/"))
        login_page = path == "/admin/login"
        player_area = path == "/device/activate" or path.startswith("/player/")
        protected = protected and not login_page
        if not protected and not login_page and not player_area:
            return await self.app(scope, receive, send)
        application = scope["app"]
        settings = application.state.auth_settings
        context = None
        if not transport_allowed(request, settings):
            response = denied(request, 503, "Transporte seguro necessário. Use HTTPS ou o teste local isolado configurado pelo operador.")
            return await response(scope, receive, send)
        try:
            if protected:
                context = await run_in_threadpool(auth.authenticate, application.state.engine, settings,
                                                  application.state.auth_clock, request.cookies.get(settings.session_cookie_name))
                scope.setdefault("state", {})["auth"] = context
                if path.startswith("/api/screens") and scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
                    if not auth.csrf_matches(context, request.headers.get("X-CSRF-Token")):
                        raise auth.AuthError(403, "Formulário expirado ou inválido.")
        except auth.AuthError as exc:
            if exc.status_code == 401 and scope["method"] in {"GET", "HEAD"} and path.startswith("/admin"):
                response = RedirectResponse("/admin/login", status_code=303, headers={"Cache-Control": "no-store"})
                clear_cookie(response, settings.session_cookie_name, settings)
            else:
                response = denied(request, exc.status_code, str(exc))
            return await response(scope, receive, send)
        except SQLAlchemyError:
            return await denied(request, 503, "Administração temporariamente indisponível.")(scope, receive, send)

        async def safe_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "private, no-store" if player_area else "no-store"
                headers["Referrer-Policy"] = "no-referrer"
                headers.setdefault("X-Content-Type-Options", "nosniff")
                if headers.get("content-type", "").startswith("text/html"):
                    headers.setdefault("Content-Security-Policy", HTML_CSP)
                # GETs protegidos e respostas negadas não escrevem no banco.
                # Atividade é renovada somente em mutações autorizadas com sucesso.
                if context and message["status"] < 400 and scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
                    try:
                        await run_in_threadpool(auth.touch_session, application.state.engine, settings,
                                                application.state.auth_clock, context)
                    except SQLAlchemyError:
                        # Não estender a sessão em memória: o timeout persistido permanece.
                        pass
            await send(message)
        await self.app(scope, receive, safe_send)


async def require_form_csrf(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    form = await request.form()
    tokens = form.getlist("csrf_token")
    context = getattr(request.state, "auth", None)
    if context is None or len(tokens) != 1 or not auth.csrf_matches(context, tokens[0]):
        raise HTTPException(status_code=403, detail="Formulário expirado ou inválido.")
