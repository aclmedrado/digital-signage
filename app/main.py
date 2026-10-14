from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from app.database import Base, engine
from app.routes.admin.screens import router as admin_router
from app.routes.admin.media import render_form as render_media_form, router as admin_media_router
from app.routes.media import router as media_router
from app.routes.screens import router


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(app.state.engine)
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.state.engine = engine
app.include_router(router)
app.include_router(admin_router)
app.include_router(admin_media_router)
app.include_router(media_router)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")


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
