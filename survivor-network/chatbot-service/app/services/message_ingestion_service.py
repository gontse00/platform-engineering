"""Message ingestion: LLM conversation -> crisis safeguard -> graph-core triage.

Key improvement: passes pre-parsed intake fields from chatbot-service LLM
directly to graph-core, so graph-core can skip its own intake parsing LLM call.
This reduces total LLM calls from 4 per message to 2.

Uses AssessmentContext as the canonical DTO for all graph-core calls,
ensuring consistency between message-time triage and submit-time case creation.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.clients.graph_core_client import GraphCoreClient, GraphCoreUnavailableError
from app.clients.llm_client import LLMClient
from app.domain.constants import PrimaryNeed
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.assessment_context import AssessmentContext
from app.services.intake_state_service import IntakeStateService

logger = logging.getLogger(__name__)


class MessageIngestionService:
    @staticmethod
    def _find_existing_message(
        db: Session,
        session: ChatSessionDB,
        client_message_id: str | None,
    ) -> ChatMessageDB | None:
        if not client_message_id:
            return None

        return (
            db.query(ChatMessageDB)
            .filter(
                ChatMessageDB.session_id == session.id,
                ChatMessageDB.role == "user",
                ChatMessageDB.client_message_id == client_message_id,
            )
            .first()
        )

    @staticmethod
    def _safe_case_update(session: ChatSessionDB) -> None:
        if not session.provisional_case_id:
            return

        state = dict(session.state_json or {})
        payload = {
            "session_id": str(session.id),
            "immediate_danger": state.get("immediate_danger"),
            "injury_status": state.get("injury_status"),
            "safe_contact_method": state.get("safe_contact_method"),
            "location": state.get("location"),
            "primary_need": state.get("primary_need"),
            "conversation_summary": state.get("incident_summary"),
        }

        try:
            graph = GraphCoreClient()
            graph.update_case_context(session.provisional_case_id, payload)
        except GraphCoreUnavailableError:
            pass

    @staticmethod
    def process_user_message(
        db: Session,
        session: ChatSessionDB,
        message: str,
        client_message_id: str | None = None,
        location: dict | None = None,
    ) -> dict[str, Any]:
        if session.status == "closed":
            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "bot_message": "This session is closed and cannot accept new messages.",
                "needs_more_info": False,
                "missing_fields": [],
                "escalation": None,
                "provisional_case": None,
                "latest_assessment": session.state_json.get("latest_graph_assessment") if session.state_json else None,
            }

        existing = MessageIngestionService._find_existing_message(db, session, client_message_id)
        if existing:
            state = dict(session.state_json or {})
            missing = IntakeStateService.missing_fields(state)
            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "bot_message": "This message was already received. Continuing with the current session state.",
                "needs_more_info": bool(missing),
                "missing_fields": missing,
                "escalation": state.get("latest_graph_assessment", {}).get("escalation"),
                "provisional_case": (
                    {"id": session.provisional_case_id} if session.provisional_case_id else None
                ),
                "latest_assessment": state.get("latest_graph_assessment"),
            }

        # --- LLM-powered conversation ---
        current_state = dict(session.state_json or {})

        # Apply browser/manual location coordinates if provided
        if location:
            current_state = IntakeStateService.apply_location(current_state, location)
            session.state_json = dict(current_state)

        history = list(current_state.get("history", []))
        history.append({"role": "user", "content": message})

        llm = LLMClient()
        llm_result = llm.process_message(
            conversation_history=history,
            current_state=current_state,
            user_message=message,
        )

        bot_message = llm_result.get("bot_message", "")
        extracted_fields = llm_result.get("extracted_fields", {})
        crisis_override = llm_result.get("crisis_override")

        # If crisis safeguard detected immediate danger, force the field
        if crisis_override and crisis_override.get("immediate_danger"):
            extracted_fields["immediate_danger"] = True

        # Update state with LLM-extracted fields
        updated_state = IntakeStateService.apply_user_message(
            current_state, message, llm_extracted=extracted_fields
        )
        updated_state = IntakeStateService.apply_bot_message(updated_state, bot_message)
        session.state_json = dict(updated_state)
        session.last_user_message_at = datetime.utcnow()

        # --- Build canonical assessment context ---
        # Serialize crisis_override for graph-core (convert enums to strings)
        crisis_data = None
        if crisis_override:
            crisis_data = {
                "min_urgency": crisis_override["min_urgency"].value
                    if hasattr(crisis_override["min_urgency"], "value")
                    else str(crisis_override["min_urgency"]),
                "min_safety": crisis_override["min_safety"].value
                    if hasattr(crisis_override["min_safety"], "value")
                    else str(crisis_override["min_safety"]),
                "reasons": crisis_override.get("reasons", []),
                "immediate_danger": crisis_override.get("immediate_danger", False),
            }

        ctx = AssessmentContext.from_session_state(
            state=dict(session.state_json),
            latest_message=message,
            crisis_override=crisis_data,
        )

        # Store crisis_override in state so submit flow can reuse it
        if crisis_data:
            st = dict(session.state_json)
            st["latest_crisis_override"] = crisis_data
            session.state_json = st

        # --- Graph-core triage assessment ---
        graph = GraphCoreClient()
        assessment = None

        try:
            assessment = graph.assess_triage(
                message=ctx.message,
                top_k=5,
                pre_parsed=ctx.pre_parsed,
                crisis_override=ctx.crisis_override,
                latitude=ctx.latitude,
                longitude=ctx.longitude,
            )

            updated_state = dict(session.state_json or {})
            updated_state["latest_graph_assessment"] = assessment
            session.state_json = updated_state
            session.last_assessed_at = datetime.utcnow()
        except GraphCoreUnavailableError:
            logger.warning("Graph-core unavailable for triage assessment")

        # --- Auto-escalation for critical/urgent cases ---
        triage = (assessment or {}).get("triage", {})
        escalation = (assessment or {}).get("escalation", {})

        if triage.get("urgency") in {"critical", "urgent"} and not session.provisional_case_id:
            try:
                case_result = graph.create_case(
                    message=ctx.message,
                    top_k=5,
                    create_referrals=True,
                    pre_parsed=ctx.pre_parsed,
                    crisis_override=ctx.crisis_override,
                    latitude=ctx.latitude,
                    longitude=ctx.longitude,
                )
                session.provisional_case_id = case_result["persisted"]["case"]["id"]
                session.latest_urgency = case_result["triage"]["urgency"]
                session.latest_queue = case_result["escalation"]["queue"]
                session.escalated = bool(case_result["escalation"]["escalate"])
                session.stage = "collecting_followup_after_escalation"
                escalation = case_result["escalation"]
            except GraphCoreUnavailableError:
                logger.warning("Graph-core unavailable for case creation")

        # Enrich existing case with new info
        if session.provisional_case_id:
            MessageIngestionService._safe_case_update(session)

        missing = IntakeStateService.missing_fields(session.state_json or {})

        if session.provisional_case_id:
            session.stage = "ready_for_submission" if not missing else "collecting_followup_after_escalation"
        else:
            session.stage = "ready_for_submission" if not missing else "collecting_required_fields"

        # Persist messages
        db.add(
            ChatMessageDB(
                session_id=session.id,
                role="user",
                content=message,
                client_message_id=client_message_id,
                extracted_json=extracted_fields if extracted_fields else {},
            )
        )
        db.add(
            ChatMessageDB(
                session_id=session.id,
                role="assistant",
                content=bot_message,
                extracted_json={},
            )
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": str(session.id),
            "status": session.status,
            "stage": session.stage,
            "bot_message": bot_message,
            "needs_more_info": bool(missing),
            "missing_fields": missing,
            "escalation": escalation if escalation else None,
            "provisional_case": (
                {"id": session.provisional_case_id} if session.provisional_case_id else None
            ),
            "latest_assessment": assessment,
        }
