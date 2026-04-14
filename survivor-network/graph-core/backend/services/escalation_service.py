"""Escalation service — now fully deterministic (no LLM call).

Escalation routing follows clear rules based on urgency and safety_risk.
This eliminates the third LLM call that was previously used here.
"""

import logging

from domain.constants import determine_escalation
from services.intake_service import IntakeParseResult

logger = logging.getLogger(__name__)


class EscalationService:
    """Deterministic escalation assessment based on triage urgency and safety risk."""

    @staticmethod
    def assess_escalation(triage: dict, parsed: IntakeParseResult) -> dict:
        urgency = triage.get("urgency", "standard")
        safety_risk = triage.get("safety_risk", "low")

        result = determine_escalation(urgency, safety_risk)

        # Enrich actions with barrier-aware notes
        if parsed.normalized_barriers and result["escalate"]:
            barrier_note = {
                "action": f"Account for barriers: {', '.join(parsed.normalized_barriers)}",
                "target": result["queue"],
                "priority": result["level"],
                "reason": "Barriers may affect service delivery — response team should plan accordingly",
            }
            result["actions"].append(barrier_note)

        # DV/assault cases always get safety planning note
        incident_types = triage.get("incident_types", [])
        dv_incidents = {"Domestic Violence", "Assault", "Sexual Violence"}
        if dv_incidents.intersection(set(incident_types)) and result["escalate"]:
            result["actions"].append({
                "action": "Include safety planning and legal review",
                "target": result["queue"],
                "priority": result["level"],
                "reason": "DV/assault case requires coordinated safety + legal response",
            })

        return result
