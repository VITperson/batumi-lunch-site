"""FastAPI application entrypoint placeholder."""

from fastapi import FastAPI

app = FastAPI(title="Batumi Lunch API", version="0.1.0")


@app.get("/healthz", tags=["internal"])
async def healthz() -> dict[str, str]:
    """Basic health endpoint; will be expanded with real checks."""
    return {"status": "ok"}


@app.get("/readyz", tags=["internal"])
async def readyz() -> dict[str, str]:
    """Readiness probe placeholder."""
    return {"status": "starting"}


# TODO: include router setup, middleware, lifespan management once core is implemented.
