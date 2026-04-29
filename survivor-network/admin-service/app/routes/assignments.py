"""Assignment routes with safety checks.

Safety rules enforced here:
- Do not assign offline/busy/suspended participants
- high/critical safety_risk requires admin_verified or higher
- critical urgency requires verified participant
- counsellor/legal/medical assignments should match participant capabilities
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_admin
from app.config import settings
from app.schemas.assignments import AssignRequest, AssignResponse, RecommendRequest
from app.utils.http import safe_get_json, safe_post_json

router = APIRouter(prefix="/admin/cases", tags=["assignments"])

VERIFIED_STATUSES = {"admin_verified", "organization_verified", "background_checked"}
BLOCKED_AVAILABILITY = {"offline", "busy", "suspended"}

# Map assignment types to participant capability fields
CAPABILITY_MAP = {
    "counsellor": "can_offer_counselling",
    "legal_advisor": "can_offer_legal_help",
    "medical_support": "can_handle_medical",
    "driver": "can_transport_people",
}


@router.post("/{case_id}/assign", response_model=AssignResponse)
async def assign_participant(
    case_id: str,
    payload: AssignRequest,
    admin: dict = Depends(get_current_admin),
):
    warnings: list[str] = []

    # Fetch case
    case_data, err = await safe_get_json(f"{settings.incident_service_url}/cases/{case_id}")
    if err:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")

    # Fetch participant
    part_data, err = await safe_get_json(
        f"{settings.participant_service_url}/participants/{payload.participant_id}"
    )
    if err:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")

    # --- Safety checks ---
    avail = part_data.get("availability_status", "offline")
    if avail in BLOCKED_AVAILABILITY:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign participant with availability_status={avail}",
        )

    verification = part_data.get("verification_status", "unverified")
    safety_risk = case_data.get("safety_risk", "low")
    urgency = case_data.get("urgency", "medium")

    # High/immediate safety risk requires verified helper
    if safety_risk in ("high", "immediate") and verification not in VERIFIED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Case safety_risk={safety_risk} requires admin_verified or higher. "
                   f"Participant verification_status={verification}",
        )

    # Critical urgency requires at least phone_verified
    if urgency == "critical" and verification == "unverified":
        raise HTTPException(
            status_code=400,
            detail=f"Case urgency=critical requires verified participant. "
                   f"Participant verification_status={verification}",
        )

    # Check capability match for specialized roles
    cap_field = CAPABILITY_MAP.get(payload.assignment_type)
    if cap_field and not part_data.get(cap_field, False):
        warnings.append(
            f"Participant may not have capability for {payload.assignment_type} "
            f"({cap_field}=false). Proceeding with warning."
        )

    # --- Create assignment via incident-service ---
    assignment_result, err = await safe_post_json(
        f"{settings.incident_service_url}/cases/{case_id}/assignments",
        {"participant_id": payload.participant_id, "role": payload.assignment_type},
    )
    if err:
        raise HTTPException(status_code=503, detail=f"Assignment failed: {err}")

    # Optional: notify participant
    if payload.notify_participant:
        _, notif_err = await safe_post_json(
            f"{settings.notification_service_url}/notifications",
            {
                "channel": "in_app",
                "recipient": payload.participant_id,
                "subject": f"New assignment: case {case_id}",
                "message": payload.note or f"You have been assigned as {payload.assignment_type}",
                "related_case_id": case_id,
                "related_participant_id": payload.participant_id,
            },
        )
        if notif_err:
            warnings.append(f"notification-service unavailable: {notif_err}")

    return AssignResponse(
        assigned=True,
        case_id=case_id,
        participant_id=payload.participant_id,
        assignment=assignment_result,
        warnings=warnings,
    )


@router.post("/{case_id}/recommend-participants")
async def recommend_participants(
    case_id: str,
    payload: RecommendRequest,
    admin: dict = Depends(get_current_admin),
):
    # Search available participants
    search_result, err = await safe_post_json(
        f"{settings.participant_service_url}/participants/search-available",
        {
            "urgency": payload.urgency,
            "safety_risk": payload.safety_risk,
            "needs": payload.needs,
            "latitude": None,
            "longitude": None,
            "radius_km": 20.0,
        },
    )
    if err:
        raise HTTPException(status_code=503, detail=f"participant-service unavailable: {err}")

    return search_result
