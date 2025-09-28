from __future__ import annotations

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from app.main import app


def main() -> None:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    output_path = Path("openapi.json")
    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2))
    print(f"OpenAPI schema written to {output_path.resolve()}")


if __name__ == "__main__":
    main()
