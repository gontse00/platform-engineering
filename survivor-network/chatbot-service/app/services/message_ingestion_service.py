from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.clients.graph_core_client import GraphCoreClient, GraphCoreUnavailableError
from app.models.session import ChatMessageDB, ChatSessionDB
from app.services.intake_state_service import IntakeStateService
from app.services.question_planner import QuestionPlanner
from app.services.response_assembly_service import ResponseAssemblyService


def _build_assessment_message(state: dict[str, Any], latest_message: str) -> str:
    parts: list[str] = []

    if state.get("incident_summary"):
        parts.append(state["incident_summary"])

    if state.get("location"):
        parts.append(f"Location: {state['location']}")

    if state.get("immediate_danger") is True:
        parts.append("User is in immediate danger")
    elif state.get("immediate_danger") is False:
        parts.append("User is not in immediate danger")

    if state.get("injury_status") == "injured":
        parts.append("User is injured")
    elif state.get("injury_status") == "not_injured":
        parts.append("User is not injured")

    if state.get("primary_need"):
        parts.append(f"Primary need: {state['primary_need']}")

    if state.get("safe_contact_method"):
        parts.append(f"Safe contact method: {state['safe_contact_method']}")

    parts.append(f"Latest user message: {latest_message}")

    return ". ".join(parts)


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
            # Do not fail the chat turn just because background case enrichment failed.
            pass

    @staticmethod
    def process_user_message(
        db: Session,
        session: ChatSessionDB,
        message: str,
        client_message_id: str | None = None,
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

        updated_state = IntakeStateService.apply_user_message(session.state_json or {}, message)
        session.state_json = dict(updated_state)
        session.last_user_message_at = datetime.utcnow()

        graph = GraphCoreClient()
        assessment = None

        try:
            assessment_message = _build_assessment_message(session.state_json, message)
            assessment = graph.assess_triage(message=assessment_message, top_k=5)

            updated_state = dict(session.state_json or {})
            updated_state["latest_graph_assessment"] = assessment
            session.state_json = updated_state
            session.last_assessed_at = datetime.utcnow()
        except GraphCoreUnavailableError:
            missing = IntakeStateService.missing_fields(session.state_json or {})

            db.add(
                ChatMessageDB(
                    session_id=session.id,
                    role="user",
                    content=message,
                    client_message_id=client_message_id,
                    extracted_json={},
                )
            )
            db.add(
                ChatMessageDB(
                    session_id=session.id,
                    role="assistant",
                    content="I saved your message, but I’m having trouble completing the full assessment right now. If you are in immediate danger, please seek emergency help now while I continue trying to route support.",
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
                "bot_message": "I saved your message, but I’m having trouble completing the full assessment right now. If you are in immediate danger, please seek emergency help now while I continue trying to route support.",
                "needs_more_info": bool(missing),
                "missing_fields": missing,
                "escalation": None,
                "provisional_case": (
                    {"id": session.provisional_case_id} if session.provisional_case_id else None
                ),
                "latest_assessment": (session.state_json or {}).get("latest_graph_assessment"),
            }

        triage = assessment.get("triage", {})
        escalation = assessment.get("escalation", {})

        if triage.get("urgency") in {"critical", "urgent"} and not session.provisional_case_id:
            case_result = graph.create_case(message=assessment_message, top_k=5, create_referrals=True)
            session.provisional_case_id = case_result["persisted"]["case"]["id"]
            session.latest_urgency = case_result["triage"]["urgency"]
            session.latest_queue = case_result["escalation"]["queue"]
            session.escalated = bool(case_result["escalation"]["escalate"])
            session.stage = "collecting_followup_after_escalation"

            bot_message = ResponseAssemblyService.emergency_message(case_result["escalation"]["queue"])
            missing = IntakeStateService.missing_fields(session.state_json or {})

            db.add(
                ChatMessageDB(
                    session_id=session.id,
                    role="user",
                    content=message,
                    client_message_id=client_message_id,
                    extracted_json={},
                )
            )
            db.add(ChatMessageDB(session_id=session.id, role="assistant", content=bot_message, extracted_json={}))
            db.add(session)
            db.commit()
            db.refresh(session)

            return {
                "session_id": str(session.id),
                "status": session.status,
                "stage": session.stage,
                "bot_message": bot_message + " " + QuestionPlanner.next_question(missing),
                "needs_more_info": True,
                "missing_fields": missing,
                "escalation": case_result["escalation"],
                "provisional_case": case_result["persisted"]["case"],
                "latest_assessment": assessment,
            }

        # Existing case: enrich it instead of creating a second one.
        if session.provisional_case_id:
            MessageIngestionService._safe_case_update(session)

        missing = IntakeStateService.missing_fields(session.state_json or {})

        if session.provisional_case_id:
            session.stage = "ready_for_submission" if not missing else "collecting_followup_after_escalation"
        else:
            session.stage = "ready_for_submission" if not missing else "collecting_required_fields"

        if not missing:
            question = "I have enough information now. You can submit the case."
        else:
            question = QuestionPlanner.next_question(missing)

        db.add(
            ChatMessageDB(
                session_id=session.id,
                role="user",
                content=message,
                client_message_id=client_message_id,
                extracted_json={},
            )
        )
        db.add(ChatMessageDB(session_id=session.id, role="assistant", content=question, extracted_json={}))
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": str(session.id),
            "status": session.status,
            "stage": session.stage,
            "bot_message": ResponseAssemblyService.standard_message(question),
            "needs_more_info": bool(missing),
            "missing_fields": missing,
            "escalation": escalation,
            "provisional_case": (
                {"id": session.provisional_case_id} if session.provisional_case_id else None
            ),
            "latest_assessment": assessment,
        }
