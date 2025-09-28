from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from .api.v1.router import router as api_router
from .core.config import settings
from .core.logging import configure_logging
from .db.session import engine

configure_logging()

_redis_client: Redis | None = Redis.from_url(str(settings.redis_url), decode_responses=True) if settings.redis_url else None

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_allow_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/healthz", tags=["monitoring"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["monitoring"])
async def readyz() -> dict[str, str]:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        if _redis_client:
            await _redis_client.ping()
    except Exception:
        return {"status": "degraded"}
    return {"status": "ready"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Batumi Lunch API"}


__all__ = ["app"]
