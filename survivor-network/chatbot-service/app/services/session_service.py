import logging

from sqlalchemy.orm import Session

from app.clients.llm_client import LLMClient
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.intake_state_service import IntakeStateService
from app.services.message_ingestion_service import MessageIngestionService

logger = logging.getLogger(__name__)


class SessionService:
    @staticmethod
    def start_session(db: Session, initial_message: str | None = None, location: dict | None = None) -> dict:
        initial_state = IntakeStateService.initial_state()
        if location:
            initial_state = IntakeStateService.apply_location(initial_state, location)

        session = ChatSessionDB(
            state_json=initial_state,
            status="active",
            stage="initial",
        )
        db.add(session)
        db.flush()

        try:
            llm = LLMClient()
            opening = llm.generate_opening()
        except Exception:
            logger.exception("LLM opening generation failed, using fallback")
            opening = "I'm here to help. You're safe to share what's happening, and I'll do my best to connect you with the right support."

        # Store opening in conversation history
        state = dict(session.state_json)
        state["history"] = [{"role": "assistant", "content": opening}]
        session.state_json = state

        db.add(ChatMessageDB(session_id=session.id, role="assistant", content=opening, extracted_json={}))

        db.commit()
        db.refresh(session)

        if initial_message:
            return MessageIngestionService.process_user_message(
                db, session, initial_message, client_message_id=None, location=location,
            )

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
