from datetime import datetime
from sqlalchemy.orm import Session

from app.clients.graph_core_client import GraphCoreClient, GraphCoreUnavailableError
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.intake_state_service import IntakeStateService


class SessionSubmitService:
    @staticmethod
    def _safe_case_update(session: ChatSessionDB) -> None:
        if not session.provisional_case_id:
            return

        state = session.state_json or {}
        payload = {
            "session_id": str(session.id),
            "immediate_danger": state.get("immediate_danger"),
            "injury_status": state.get("injury_status"),
            "safe_contact_method": state.get("safe_contact_method"),
            "location": state.get("location"),
            "primary_need": state.get("primary_need"),
            "conversation_summary": state.get("incident_summary"),
            "submission_mode": state.get("submission_mode"),
        }

        try:
            graph = GraphCoreClient()
            graph.update_case_context(session.provisional_case_id, payload)
        except GraphCoreUnavailableError:
            pass

    @staticmethod
    def submit_session(db: Session, session: ChatSessionDB) -> dict:
        state = dict(session.state_json or {})
        missing = IntakeStateService.missing_fields(state)

        if session.status == "closed":
            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "provisional_case_id": session.provisional_case_id,
                "submitted": False,
                "missing_fields": missing,
                "state": session.state_json,
                "message": "This session is closed and cannot be submitted.",
            }

        if session.status == "submitted":
            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "provisional_case_id": session.provisional_case_id,
                "submitted": True,
                "missing_fields": missing,
                "state": session.state_json,
                "message": "This session has already been submitted.",
            }

        if not session.provisional_case_id and missing:
            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "provisional_case_id": session.provisional_case_id,
                "submitted": False,
                "missing_fields": missing,
                "state": session.state_json,
                "message": "More information is required before submission.",
            }

        if not session.provisional_case_id:
            incident_summary = state.get("incident_summary") or "User requested help"
            graph = GraphCoreClient()
            case_result = graph.create_case(
                message=incident_summary,
                top_k=5,
                create_referrals=True,
            )
            session.provisional_case_id = case_result["persisted"]["case"]["id"]
            session.latest_urgency = case_result["triage"]["urgency"]
            session.latest_queue = case_result["escalation"]["queue"]
            session.escalated = bool(case_result["escalation"]["escalate"])

        state["submission_mode"] = "provisional_partial" if missing else "complete"
        session.state_json = state
        session.status = "submitted"
        session.stage = "submitted"
        session.submitted_at = datetime.utcnow()

        SessionSubmitService._safe_case_update(session)

        bot_message = "Your case has been submitted. We will continue using the information you provided."
        db.add(ChatMessageDB(session_id=session.id, role="assistant", content=bot_message, extracted_json={}))
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": str(session.id),
            "status": session.status,
            "stage": session.stage,
            "provisional_case_id": session.provisional_case_id,
            "submitted": True,
            "missing_fields": missing,
            "state": session.state_json,
            "message": bot_message,
        }