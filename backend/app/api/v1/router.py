from fastapi import APIRouter

from .endpoints import routers as endpoint_routers

router = APIRouter(prefix="/api/v1")

for sub_router in endpoint_routers:
    router.include_router(sub_router)


@router.get("/ping", tags=["monitoring"])
async def ping() -> dict[str, str]:
    return {"message": "pong"}
