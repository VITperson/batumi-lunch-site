"""FastAPI application entrypoint."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.endpoints import admin, auth, menu, orders
from app.core.config import settings
from app.core.logging import configure_logging, set_trace_id

configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0", openapi_url=f"{settings.api_v1_prefix}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static media (temporary local storage until S3 integration)
MEDIA_ROOT = Path(__file__).resolve().parents[2] / "storage" / "menu"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media/menu", StaticFiles(directory=str(MEDIA_ROOT), check_dir=False), name="menu-media")


@app.middleware("http")
async def add_request_id(request: Request, call_next):  # type: ignore[override]
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_trace_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_db)) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - readiness path
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(exc)})
    return JSONResponse({"status": "ready"})


app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(menu.router, prefix=settings.api_v1_prefix)
app.include_router(orders.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Batumi Lunch API", "docs": f"{settings.api_v1_prefix}/docs"}
