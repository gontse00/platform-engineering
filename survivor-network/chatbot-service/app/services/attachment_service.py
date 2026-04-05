from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.session import ChatAttachmentDB, ChatSessionDB


class AttachmentService:
    @staticmethod
    def save_attachment(db: Session, session: ChatSessionDB, file: UploadFile) -> ChatAttachmentDB:
        target_dir = Path(settings.attachment_storage_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "").suffix
        filename = f"{uuid4()}{suffix}"
        filepath = target_dir / filename

        with open(filepath, "wb") as out:
            out.write(file.file.read())

        attachment = ChatAttachmentDB(
            session_id=session.id,
            attachment_type=file.content_type or "application/octet-stream",
            storage_path=str(filepath),
            original_filename=file.filename,
            metadata_json={},
        )
        db.add(attachment)

        state = dict(session.state_json or {})
        state["attachments"] = list(state.get("attachments", []))
        state["attachments"].append(
            {
                "attachment_id": str(attachment.id) if attachment.id else None,
                "filename": file.filename,
                "content_type": file.content_type,
            }
        )
        session.state_json = state

        db.add(session)
        db.commit()
        db.refresh(attachment)
        return attachment