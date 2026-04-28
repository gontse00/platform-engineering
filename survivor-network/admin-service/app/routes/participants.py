from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_admin
from app.config import settings
from app.schemas.participants import VerificationUpdateRequest, AvailabilityUpdateRequest
from app.utils.http import safe_get_json, safe_patch_json

router = APIRouter(prefix="/admin/participants", tags=["participants"])


@router.get("/{participant_id}")
async def get_participant(participant_id: str, admin: dict = Depends(get_current_admin)):
    warnings: list[str] = []

    data, err = await safe_get_json(f"{settings.participant_service_url}/participants/{participant_id}")
    if err:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")

    # Optional: graph relationships
    graph_data, graph_err = await safe_get_json(
        f"{settings.graph_core_url}/graph/nodes/{participant_id}/neighbors"
    )
    if graph_err:
        warnings.append("graph-core context unavailable")

    return {
        "participant": data,
        "graph_context": graph_data,
        "warnings": warnings,
    }


@router.patch("/{participant_id}/verification")
async def update_verification(
    participant_id: str,
    payload: VerificationUpdateRequest,
    admin: dict = Depends(get_current_admin),
):
    # TODO: add audit trail when audit-service exists
    result, err = await safe_patch_json(
        f"{settings.participant_service_url}/participants/{participant_id}/verification",
        {"verification_status": payload.verification_status},
    )
    if err:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")
    return result


@router.patch("/{participant_id}/availability")
async def update_availability(
    participant_id: str,
    payload: AvailabilityUpdateRequest,
    admin: dict = Depends(get_current_admin),
):
    result, err = await safe_patch_json(
        f"{settings.participant_service_url}/participants/{participant_id}/availability",
        {"availability_status": payload.availability_status},
    )
    if err:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")
    return result
