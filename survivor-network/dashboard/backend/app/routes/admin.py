"""
Admin Routes (Protected) - Local Survivor Network
Admin endpoints for mission and event management.
Requires Local JWT Auth - user must be in the 'admins' Postgres table.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends

from ..config import DEFAULT_MAX_PARTICIPANTS
# These now point to our SQLAlchemy/Postgres logic
from ..database import get_event, create_event, list_events, delete_event
# This now uses our local JWT verification logic
from ..dependencies import verify_admin
from ..models.events import EventCreate, EventResponse


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/events", response_model=EventResponse)
async def create_new_event(data: EventCreate, admin_email: str = Depends(verify_admin)):
    """
    Create a new mission/event (admin only).
    Uses local JWT; user must exist in the 'admins' table.
    """
    # 1. Check if mission code already exists in Postgres
    existing = await get_event(data.code)
    if existing:
        raise HTTPException(status_code=409, detail="Mission code already exists")

    # 2. Prepare the data for the JSONB 'data' column
    # We explicitly set the audit trail and local timestamps
    now = datetime.now(timezone.utc)
    
    event_dict = {
        "code": data.code,
        "name": data.name,
        "description": data.description,
        "max_participants": data.max_participants or DEFAULT_MAX_PARTICIPANTS,
        "participant_count": 0,
        "created_at": now.isoformat(),
        "created_by": admin_email,  # Audit trail for the survivor cell
        "active": True,
    }

    # 3. Store in Postgres
    await create_event(event_dict)

    # Pydantic will handle the conversion to EventResponse
    return event_dict


@router.get("/events", response_model=list[EventResponse])
async def list_all_events(admin_email: str = Depends(verify_admin)):
    """
    List all missions across the local network (admin only).
    """
    events = await list_events()
    return events


@router.delete("/events/{code}")
async def deactivate_event(code: str, admin_email: str = Depends(verify_admin)):
    """
    Deactivate a mission (admin only).
    Soft-delete pattern: updates the 'active' flag in Postgres.
    """
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Mission not found")

    await delete_event(code)

    return {
        "status": "success", 
        "message": f"Mission {code} deactivated", 
        "deactivated_by": admin_email,
        "timestamp": datetime.now(timezone.utc)
    }