from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_auth_settings
from app.database import Base, engine
from app.models import utc_now
from app.routes.admin.auth import router as auth_router
from app.routes.admin.device import router as admin_device_router
from app.routes.device import router as device_router
from app.routes.player import router as player_router
from app.routes.admin.playlists import router as admin_playlists_router
from app.routes.admin.screens import router as admin_router
from app.routes.admin.media import render_form as render_media_form, router as admin_media_router
from app.routes.media import router as media_router
from app.routes.screens import router
from app.security import AuthMiddleware, denied
from app.services.auth import AuthError, dummy_hash


@asynccontextmanager
async def lifespan(app):
    app.state.auth_settings = get_auth_settings()
    dummy_hash()
    Base.metadata.create_all(app.state.engine)
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.state.engine = engine
app.state.auth_clock = utc_now
app.add_middleware(AuthMiddleware)
app.include_router(auth_router)
app.include_router(router)
app.include_router(admin_router)
app.include_router(admin_media_router)
app.include_router(admin_playlists_router)
app.include_router(media_router)
app.include_router(admin_device_router)
app.include_router(device_router)
app.include_router(player_router)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")


@app.exception_handler(HTTPException)
async def restricted_access(request, exc):
    if request.url.path.startswith("/admin") and exc.status_code in {401, 403}:
        return denied(request, exc.status_code, "Formulário expirado ou inválido." if exc.status_code == 403 else "Autenticação necessária.")
    return await http_exception_handler(request, exc)


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, exc):
    return denied(request, 503, "Administração temporariamente indisponível.")


@app.exception_handler(AuthError)
async def credential_error(request, exc):
    return denied(request, exc.status_code, str(exc))


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    if request.method == "POST" and request.url.path == "/admin/media":
        return render_media_form(request, "", "Informe um título e selecione um arquivo válido.", 422)
    return await request_validation_exception_handler(request, exc)


@app.get("/")
def index() -> dict[str, str]:
    return {"name": "Digital Signage", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
