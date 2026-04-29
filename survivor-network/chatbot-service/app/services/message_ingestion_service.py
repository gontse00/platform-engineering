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

from app.clients.agent_service_client import (
    AgentServiceClient,
    AgentServiceUnavailableError,
    AGENT_FALLBACK_RESPONSE,
)
from app.clients.graph_core_client import GraphCoreClient, GraphCoreUnavailableError
from app.clients.incident_service_client import IncidentServiceClient, IncidentServiceUnavailableError
from app.clients.llm_client import LLMClient
from app.domain.constants import PrimaryNeed
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.assessment_context import AssessmentContext
from app.services.intake_state_service import IntakeStateService
from app.services.safety_check import run_safety_check

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
        """Best-effort graph-core context enrichment for the case.
        
        Note: The case ID now belongs to incident-service. Graph-core may not
        recognize it. This call is optional and failure is silently ignored.
        """
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
            # Expected: graph-core may not know this case ID (it's from incident-service)
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

        # --- Deterministic safety check (runs BEFORE any agent/LLM) ---
        safety_flags = run_safety_check(message)

        # --- Call agent-service for reasoning ---
        agent_result = None
        try:
            agent_client = AgentServiceClient()
            agent_result = agent_client.reason(
                session_id=str(session.id),
                message=message,
                conversation_context={
                    "known_location": current_state.get("location"),
                    "known_primary_need": current_state.get("primary_need"),
                    "known_injury_status": current_state.get("injury_status"),
                    "known_contact_method": current_state.get("safe_contact_method"),
                    "known_incident_summary": current_state.get("incident_summary"),
                    "conversation_history": history[-6:],  # last 6 messages for context
                },
                safety_flags=safety_flags,
            )
        except AgentServiceUnavailableError:
            logger.warning("agent-service unavailable — using fallback")
            agent_result = AGENT_FALLBACK_RESPONSE

        # --- Also run existing LLM path for backward compatibility ---
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
            # Create provisional case through incident-service (source of truth)
            try:
                incident_client = IncidentServiceClient()
                intake_payload = {
                    "session_id": str(session.id),
                    "message": ctx.message[:500],
                    "location_text": (session.state_json or {}).get("location"),
                    "latitude": ctx.latitude,
                    "longitude": ctx.longitude,
                    "urgency": triage.get("urgency", "urgent"),
                    "safety_risk": triage.get("safety_risk", "medium"),
                    "primary_need": (session.state_json or {}).get("primary_need"),
                    "secondary_needs": [],
                    "injury_status": (session.state_json or {}).get("injury_status"),
                    "immediate_danger": (session.state_json or {}).get("immediate_danger", False),
                    "incident_type": None,
                }
                case_result = incident_client.create_case_from_intake(intake_payload)

                session.provisional_case_id = case_result["id"]
                session.latest_urgency = case_result.get("urgency")
                session.latest_queue = escalation.get("queue")
                session.escalated = bool(escalation.get("escalate", True))
                session.stage = "collecting_followup_after_escalation"

                # Add timeline entry
                try:
                    incident_client.add_timeline_entry(
                        case_id=case_result["id"],
                        event_type="auto_escalation",
                        description=f"Auto-escalated: urgency={triage.get('urgency')}, safety={triage.get('safety_risk')}",
                        actor="chatbot-service",
                    )
                except IncidentServiceUnavailableError:
                    pass

            except IncidentServiceUnavailableError:
                logger.warning("incident-service unavailable for provisional case creation")

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
                agent_reasoning_json=agent_result,
                safety_flags_json=safety_flags,
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
