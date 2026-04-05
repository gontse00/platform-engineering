"""
Participant Routes - Local Survivor Network
Endpoints for participant registration, coordinate assignment, and MinIO file uploads.
"""

import secrets
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File

from ..config import MAP_WIDTH, MAP_HEIGHT
from ..database import (
    get_event,
    get_participant,
    create_participant,
    update_participant,
    check_username_exists,
)
from ..storage import upload_avatar_image, get_avatar_url
from ..models.participants import (
    ParticipantInit,
    ParticipantInitResponse,
    ParticipantRegister,
    ParticipantResponse,
    ParticipantUpdate,
)

router = APIRouter(prefix="/participants", tags=["Participants"])

# =============================================================================
# Lifecycle: Initialization & Coordinate Assignment
# =============================================================================

@router.post("/init", response_model=ParticipantInitResponse)
async def init_participant(data: ParticipantInit):
    """
    Initialize a new survivor. Assigns random starting coordinates within the map.
    """
    event = await get_event(data.event_code)
    if not event:
        raise HTTPException(status_code=404, detail="Mission not found")

    if not event.get("active", True):
        raise HTTPException(status_code=410, detail="Mission has been deactivated")

    # Race condition protection for names
    if await check_username_exists(data.event_code, data.username):
        raise HTTPException(status_code=409, detail="Survivor name already taken")

    # Local Logic: Generate a unique ID and random spawn point
    participant_id = secrets.token_hex(4) 
    starting_x = random.randint(10, MAP_WIDTH - 10)
    starting_y = random.randint(10, MAP_HEIGHT - 10)

    participant = {
        "participant_id": participant_id,
        "username": data.username,
        "event_code": data.event_code,
        "x": starting_x,
        "y": starting_y,
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }

    await create_participant(participant)

    return ParticipantInitResponse(
        participant_id=participant_id,
        username=data.username,
        event_code=data.event_code,
        starting_x=starting_x,
        starting_y=starting_y,
    )

# =============================================================================
# Evidence & Avatar: Local MinIO Uploads
# =============================================================================

@router.post("/{participant_id}/avatar")
async def upload_avatar(
    participant_id: str,
    portrait: UploadFile = File(...),
    icon: UploadFile = File(...),
):
    """
    Uploads survivor portraits to local MinIO storage.
    """
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Survivor not found")

    event_code = participant["event_code"]
    
    # Upload Portrait
    p_bytes = await portrait.read()
    p_path = f"avatars/{event_code}/{participant_id}/portrait.png"
    await upload_avatar_image(p_path, p_bytes, portrait.content_type)
    p_url = get_avatar_url(p_path)

    # Upload Icon
    i_bytes = await icon.read()
    i_path = f"avatars/{event_code}/{participant_id}/icon.png"
    await upload_avatar_image(i_path, i_bytes, icon.content_type)
    i_url = get_avatar_url(i_path)

    await update_participant(participant_id, {
        "portrait_url": p_url,
        "icon_url": i_url,
    })

    return {"status": "success", "portrait_url": p_url, "icon_url": i_url}

@router.post("/{participant_id}/evidence")
async def upload_evidence(
    participant_id: str,
    soil_sample: UploadFile = File(...),
    star_field: UploadFile = File(...),
    flora_recording: UploadFile = File(...),
):
    """
    Handles multimodal evidence (images/video) for Level 1 of the lab.
    """
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Survivor not found")

    event_code = participant["event_code"]
    urls = {}
    evidence_files = [
        (soil_sample, "soil_sample", "soil"),
        (star_field, "star_field", "stars"),
        (flora_recording, "flora_recording", "flora"),
    ]

    for file, filename, url_key in evidence_files:
        file_bytes = await file.read()
        # Determine extension locally
        ext = "png" if "png" in file.content_type else "jpg"
        if "video" in file.content_type: ext = "mp4"

        path = f"evidence/{event_code}/{participant_id}/{filename}.{ext}"
        await upload_avatar_image(path, file_bytes, file.content_type)
        urls[url_key] = get_avatar_url(path)

    await update_participant(participant_id, {"evidence_urls": urls})
    return {"status": "success", "evidence_urls": urls}

# =============================================================================
# Helper: Fetch Survivor Context
# =============================================================================

@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant_info(participant_id: str):
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Survivor not found")
    return participant