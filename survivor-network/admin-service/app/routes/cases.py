from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_admin
from app.config import settings
from app.schemas.cases import CaseDetailResponse, StatusUpdateRequest, EscalateRequest
from app.utils.http import safe_get_json, safe_patch_json, safe_post_json

router = APIRouter(prefix="/admin/cases", tags=["cases"])


@router.get("")
async def list_cases(
    status: str | None = None,
    urgency: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(get_current_admin),
):
    """List all cases from incident-service."""
    params: dict = {"limit": str(limit), "offset": str(offset)}
    if status:
        params["status"] = status
    if urgency:
        params["urgency"] = urgency

    data, err = await safe_get_json(f"{settings.incident_service_url}/cases", params)
    if data is None:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")
    return data


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(case_id: str, admin: dict = Depends(get_current_admin)):
    warnings: list[str] = []

    # Case from incident-service
    case_data, err = await safe_get_json(f"{settings.incident_service_url}/cases/{case_id}")
    if err:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")

    # Graph context (optional)
    graph_ctx, err = await safe_get_json(f"{settings.graph_core_url}/graph/nodes/{case_id}/neighbors")
    if err:
        warnings.append("graph-core context unavailable")
        graph_ctx = None

    # Attachments (optional)
    attachments_data, err = await safe_get_json(
        f"{settings.attachment_service_url}/attachments",
        {"owner_type": "case", "owner_id": case_id},
    )
    if err:
        warnings.append("attachment-service unavailable")
        attachments_data = None

    return CaseDetailResponse(
        case=case_data,
        graph_context=graph_ctx,
        attachments=attachments_data.get("attachments", []) if attachments_data else [],
        assignments=[],  # TODO: fetch from incident-service assignments endpoint
        warnings=warnings,
    )


@router.patch("/{case_id}/status")
async def update_case_status(
    case_id: str,
    payload: StatusUpdateRequest,
    admin: dict = Depends(get_current_admin),
):
    warnings: list[str] = []

    # Update status via incident-service
    result, err = await safe_patch_json(
        f"{settings.incident_service_url}/cases/{case_id}/status",
        {"status": payload.status, "reason": payload.note},
    )
    if err:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")

    # Add timeline note if provided
    if payload.note:
        _, timeline_err = await safe_post_json(
            f"{settings.incident_service_url}/cases/{case_id}/timeline",
            {"event_type": "admin_note", "description": payload.note, "actor": "admin"},
        )
        if timeline_err:
            warnings.append("Timeline entry failed — status was still updated")

    result["warnings"] = warnings
    return result


@router.get("/{case_id}/timeline")
async def get_case_timeline(case_id: str, admin: dict = Depends(get_current_admin)):
    """Fetch case timeline from incident-service."""
    data, err = await safe_get_json(f"{settings.incident_service_url}/cases/{case_id}/timeline")
    if err:
        raise HTTPException(status_code=503, detail=f"incident-service unavailable: {err}")
    return data


@router.post("/{case_id}/escalate")
async def escalate_case(
    case_id: str,
    payload: EscalateRequest,
    admin: dict = Depends(get_current_admin),
):
    warnings: list[str] = []

    # Add escalation timeline entry
    _, err = await safe_post_json(
        f"{settings.incident_service_url}/cases/{case_id}/timeline",
        {
            "event_type": "escalation",
            "description": f"Escalated to {payload.target}: {payload.reason}",
            "actor": "admin",
        },
    )
    if err:
        warnings.append(f"incident-service timeline unavailable: {err}")

    # Update status to escalated
    await safe_patch_json(
        f"{settings.incident_service_url}/cases/{case_id}/status",
        {"status": "triaging", "reason": f"Escalated to {payload.target}"},
    )

    # Send notification if requested
    notification_sent = False
    if payload.notify:
        _, notif_err = await safe_post_json(
            f"{settings.notification_service_url}/notifications",
            {
                "channel": "in_app",
                "recipient": payload.target,
                "subject": f"Case escalation: {case_id}",
                "message": payload.reason,
                "related_case_id": case_id,
            },
        )
        if notif_err:
            warnings.append(f"notification-service unavailable: {notif_err}")
        else:
            notification_sent = True

    return {
        "escalated": True,
        "case_id": case_id,
        "target": payload.target,
        "notification_sent": notification_sent,
        "warnings": warnings,
    }
