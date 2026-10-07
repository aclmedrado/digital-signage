from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routes.screens import router


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(app.state.engine)
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.state.engine = engine
app.include_router(router)


@app.get("/")
def index() -> dict[str, str]:
    return {"name": "Digital Signage", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
