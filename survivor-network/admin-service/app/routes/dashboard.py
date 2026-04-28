from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_admin
from app.config import settings
from app.schemas.dashboard import DashboardSummary
from app.utils.http import safe_get_json

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(admin: dict = Depends(get_current_admin)):
    warnings: list[str] = []

    # Fetch cases from incident-service
    active_cases = 0
    urgent_cases = 0
    cases_data, err = await safe_get_json(f"{settings.incident_service_url}/cases", {"limit": "200"})
    if cases_data:
        all_cases = cases_data.get("cases", [])
        active_cases = sum(1 for c in all_cases if c.get("status") not in ("resolved", "closed", "rejected"))
        urgent_cases = sum(1 for c in all_cases if c.get("urgency") in ("urgent", "critical"))
    elif err:
        warnings.append(f"incident-service unavailable: {err}")

    # Fetch participants from participant-service
    available_participants = 0
    unverified_participants = 0
    parts_data, err = await safe_get_json(f"{settings.participant_service_url}/participants", {"limit": "200"})
    if parts_data:
        all_parts = parts_data.get("participants", [])
        available_participants = sum(1 for p in all_parts if p.get("availability_status") in ("available", "on_call"))
        unverified_participants = sum(1 for p in all_parts if p.get("verification_status") == "unverified")
    elif err:
        warnings.append(f"participant-service unavailable: {err}")

    status = "ok" if not warnings else "degraded"

    return DashboardSummary(
        active_cases=active_cases,
        urgent_cases=urgent_cases,
        available_participants=available_participants,
        unverified_participants=unverified_participants,
        recent_reports=0,  # TODO: incident-service report count
        system_status=status,
        warnings=warnings,
    )


@router.get("/cases")
async def dashboard_cases(
    status: str | None = None,
    urgency: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(get_current_admin),
):
    params: dict = {"limit": str(limit), "offset": str(offset)}
    if status:
        params["status"] = status
    if urgency:
        params["urgency"] = urgency

    data, err = await safe_get_json(f"{settings.incident_service_url}/cases", params)
    if data is None:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")
    return data


@router.get("/participants")
async def dashboard_participants(
    availability_status: str | None = None,
    verification_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(get_current_admin),
):
    params: dict = {"limit": str(limit)}
    if availability_status:
        params["status"] = availability_status

    data, err = await safe_get_json(f"{settings.participant_service_url}/participants", params)
    if data is None:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")
    return data
