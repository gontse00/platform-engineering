"""Session submit service.

Creates operational cases through incident-service (source of truth for cases).
Uses graph-core only for triage/resource matching context.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.clients.graph_core_client import GraphCoreClient, GraphCoreUnavailableError
from app.clients.incident_service_client import IncidentServiceClient, IncidentServiceUnavailableError
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.assessment_context import AssessmentContext
from app.services.intake_state_service import IntakeStateService

logger = logging.getLogger(__name__)


class SessionSubmitService:
    @staticmethod
    def _safe_graph_context_update(session: ChatSessionDB) -> None:
        """Best-effort graph-core context enrichment. Non-blocking."""
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
            "submission_mode": state.get("submission_mode"),
        }

        try:
            graph = GraphCoreClient()
            graph.update_case_context(session.provisional_case_id, payload)
        except GraphCoreUnavailableError:
            logger.warning("graph-core context update failed (non-blocking)")

    @staticmethod
    def _build_intake_payload(session: ChatSessionDB, state: dict) -> dict:
        """Build the payload for incident-service /cases/from-intake."""
        assessment = state.get("latest_graph_assessment", {})
        triage = assessment.get("triage", {})

        return {
            "session_id": str(session.id),
            "message": state.get("incident_summary") or "User requested help",
            "location_text": state.get("location"),
            "latitude": state.get("latitude"),
            "longitude": state.get("longitude"),
            "urgency": triage.get("urgency", session.latest_urgency or "medium"),
            "safety_risk": triage.get("safety_risk", "low"),
            "primary_need": state.get("primary_need"),
            "secondary_needs": [],
            "injury_status": state.get("injury_status"),
            "immediate_danger": state.get("immediate_danger", False),
            "incident_type": None,  # TODO: extract from triage incident_types
        }

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

        # --- Create case via incident-service if one does not exist yet ---
        if not session.provisional_case_id:
            intake_payload = SessionSubmitService._build_intake_payload(session, state)

            try:
                incident_client = IncidentServiceClient()
                case_result = incident_client.create_case_from_intake(intake_payload)

                session.provisional_case_id = case_result["id"]
                session.latest_urgency = case_result.get("urgency")
                session.escalated = case_result.get("urgency") in ("critical", "urgent")

                # Add timeline entry
                try:
                    incident_client.add_timeline_entry(
                        case_id=case_result["id"],
                        event_type="submitted",
                        description=f"Case submitted from chatbot session {session.id}",
                        actor="chatbot-service",
                    )
                except IncidentServiceUnavailableError:
                    logger.warning("Failed to add timeline entry (non-blocking)")

            except IncidentServiceUnavailableError:
                logger.error("incident-service unavailable — cannot create case on submit")
                return {
                    "session_id": str(session.id),
                    "status": session.status,
                    "stage": session.stage,
                    "provisional_case_id": None,
                    "submitted": False,
                    "missing_fields": missing,
                    "state": session.state_json,
                    "message": "Unable to submit case — service temporarily unavailable. Please try again.",
                }

        state["submission_mode"] = "provisional_partial" if missing else "complete"
        session.state_json = state
        session.status = "submitted"
        session.stage = "submitted"
        session.submitted_at = datetime.utcnow()

        # Best-effort graph-core context enrichment
        SessionSubmitService._safe_graph_context_update(session)

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
