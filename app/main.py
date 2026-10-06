from fastapi import FastAPI


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
def index() -> dict[str, str]:
    return {"name": "Digital Signage", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
