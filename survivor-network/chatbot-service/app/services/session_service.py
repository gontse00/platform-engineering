from sqlalchemy.orm import Session

from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.intake_state_service import IntakeStateService
from app.services.message_ingestion_service import MessageIngestionService
from app.services.response_assembly_service import ResponseAssemblyService


class SessionService:
    @staticmethod
    def start_session(db: Session, initial_message: str | None = None) -> dict:
        session = ChatSessionDB(
            state_json=IntakeStateService.initial_state(),
            status="active",
            stage="initial",
        )
        db.add(session)
        db.flush()

        opening = ResponseAssemblyService.opening_message()
        db.add(ChatMessageDB(session_id=session.id, role="assistant", content=opening, extracted_json={}))

        db.commit()
        db.refresh(session)

        if initial_message:
            return MessageIngestionService.process_user_message(db, session, initial_message, client_message_id=None)

        return {
            "session_id": str(session.id),
            "status": session.status,
            "stage": session.stage,
            "bot_message": opening,
            "next_expected_fields": IntakeStateService.missing_fields(session.state_json),
        }

    @staticmethod
    def get_session(db: Session, session_id: str) -> ChatSessionDB | None:
        return db.query(ChatSessionDB).filter(ChatSessionDB.id == session_id).first()

    @staticmethod
    def ensure_message_allowed(session: ChatSessionDB) -> None:
        if session.status == "closed":
            raise ValueError("Session is closed and cannot receive new messages.")

    @staticmethod
    def ensure_submit_allowed(session: ChatSessionDB) -> None:
        if session.status == "closed":
            raise ValueError("Session is closed and cannot be submitted.")