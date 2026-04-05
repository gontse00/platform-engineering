from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.schemas import SessionAttachmentResponse
from app.services.attachment_service import AttachmentService
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["attachments"])


@router.post("/{session_id}/attachments", response_model=SessionAttachmentResponse)
def upload_attachment(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attachment = AttachmentService.save_attachment(db, session, file)
    return {
        "attachment_id": str(attachment.id),
        "attachment_type": attachment.attachment_type,
        "filename": attachment.original_filename,
    }