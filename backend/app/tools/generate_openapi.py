"""Utility to dump OpenAPI schema to disk for documentation / contracts."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.main import app


def main() -> None:
    schema = get_openapi(
        title=settings.app_name,
        version=app.version,
        routes=app.routes,
        description="Batumi Lunch API",
    )
    output = Path(__file__).resolve().parents[2] / "openapi.json"
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    print(f"OpenAPI schema written to {output}")


if __name__ == "__main__":
    main()
