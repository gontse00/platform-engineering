"""
Event Routes (Public) - Local Survivor Network
Public endpoints for mission details and participant discovery.
"""

from fastapi import APIRouter, HTTPException
from typing import List

# Points to our local Postgres/SQLAlchemy logic
from ..database import get_event, check_username_exists, list_participants_by_event
from ..models.events import EventResponse
from ..models.participants import UsernameCheckResponse, ParticipantResponse


router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/{code}", response_model=EventResponse)
async def get_event_info(code: str):
    """
    Get mission information by code.
    Used by local setup scripts to validate mission codes.
    """
    event = await get_event(code)
    
    if not event:
        raise HTTPException(status_code=404, detail="Mission not found")

    # If the mission is soft-deleted (active=False), return 410 Gone
    if not event.get("active", True):
        raise HTTPException(status_code=410, detail="Mission has been deactivated")

    return event


@router.get("/{code}/check-username/{username}", response_model=UsernameCheckResponse)
async def check_username(code: str, username: str):
    """
    Check if a survivor name is available for a mission.
    Prevents duplicate identities within the same local cell.
    """
    # Verify the mission exists in Postgres
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Our local check_username_exists uses the 'username_lower' index for speed
    exists = await check_username_exists(code, username)

    return UsernameCheckResponse(
        available=not exists,
        username=username
    )


@router.get("/{code}/participants", response_model=List[ParticipantResponse])
async def list_event_participants(code: str):
    """
    List all survivors for a mission.
    Used by the React/Three.js frontend to render markers on the 3D map.
    """
    # Verify mission exists
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Mission not found")

    participants = await list_participants_by_event(code)

    # Filter for active survivors who have finished registration
    # Note: 'registered_at' is stored in the JSONB data column
    # active_participants = [
    #     p for p in participants 
    #     if p.get("active", True) and p.get("registered_at")
    # ]

    return [p for p in participants if p.get("active", True)]