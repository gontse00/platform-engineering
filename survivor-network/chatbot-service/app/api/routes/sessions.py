from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.schemas import (
    SessionMessageRequest,
    SessionStateResponse,
    SessionTurnResponse,
    StartSessionRequest,
    StartSessionResponse,
    SubmitSessionResponse,
)
from app.services.message_ingestion_service import MessageIngestionService
from app.services.session_service import SessionService
from app.services.session_submit_service import SessionSubmitService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=StartSessionResponse | SessionTurnResponse)
def start_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    location_dict = payload.location.model_dump() if payload.location else None
    return SessionService.start_session(db, initial_message=payload.initial_message, location=location_dict)


@router.post("/{session_id}/message", response_model=SessionTurnResponse)
def send_message(session_id: str, payload: SessionMessageRequest, db: Session = Depends(get_db)):
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        SessionService.ensure_message_allowed(session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    location_dict = payload.location.model_dump() if payload.location else None
    return MessageIngestionService.process_user_message(
        db,
        session,
        payload.message,
        client_message_id=payload.client_message_id,
        location=location_dict,
    )


@router.post("/{session_id}/submit", response_model=SubmitSessionResponse)
def submit_session(session_id: str, db: Session = Depends(get_db)):
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        SessionService.ensure_submit_allowed(session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return SessionSubmitService.submit_session(db, session)


@router.get("/{session_id}", response_model=SessionStateResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": str(session.id),
        "status": session.status,
        "stage": session.stage,
        "escalated": session.escalated,
        "provisional_case_id": session.provisional_case_id,
        "latest_urgency": session.latest_urgency,
        "latest_queue": session.latest_queue,
        "state": session.state_json,
        "message_count": len(session.messages),
        "attachment_count": len(session.attachments),
    }