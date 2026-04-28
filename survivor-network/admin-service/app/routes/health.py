from fastapi import APIRouter

from app.config import settings
from app.utils.http import check_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready():
    deps = {
        "graph_core": await check_health(settings.graph_core_url),
        "incident_service": await check_health(settings.incident_service_url),
        "participant_service": await check_health(settings.participant_service_url),
        "attachment_service": await check_health(settings.attachment_service_url),
        "notification_service": await check_health(settings.notification_service_url),
    }
    all_ok = all(v == "ok" for v in deps.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "service": settings.service_name,
        "dependencies": deps,
    }
