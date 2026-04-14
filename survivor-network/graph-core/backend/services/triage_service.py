"""Triage assessment service.

LLM-powered urgency/safety scoring with deterministic crisis safeguard boost.
If chatbot-service detected crisis keywords, the min_urgency and min_safety
from those keywords are used as a FLOOR — the LLM can raise them higher but
never lower them below the deterministic minimum.
"""

import logging

from clients.llm_client import GraphCoreLLMClient
from domain.constants import boost_urgency, boost_safety, normalize_urgency, normalize_safety_risk
from services.intake_service import IntakeParseResult

logger = logging.getLogger(__name__)


class TriageService:
    """LLM-powered triage with deterministic crisis safeguard."""

    @staticmethod
    def assess_triage(
        message: str,
        parsed: IntakeParseResult,
        crisis_override: dict | None = None,
    ) -> dict:
        intake_data = {
            "normalized_location": parsed.normalized_location,
            "primary_needs": parsed.primary_needs,
            "derived_support_needs": parsed.derived_support_needs,
            "normalized_barriers": parsed.normalized_barriers,
        }

        llm = GraphCoreLLMClient()
        result = llm.assess_triage(message, intake_data)

        # Normalize enum values (already done by Pydantic in llm_client,
        # but belt-and-suspenders for safety)
        urgency = normalize_urgency(result.get("urgency"))
        safety_risk = normalize_safety_risk(result.get("safety_risk"))

        # --- Deterministic crisis safeguard boost ---
        # If chatbot-service detected crisis keywords, enforce minimum levels.
        # The LLM can RAISE urgency higher, but never lower it below the
        # keyword-detected minimum.
        safeguard_reasons: list[str] = []

        if crisis_override:
            min_urg = normalize_urgency(crisis_override.get("min_urgency"))
            min_saf = normalize_safety_risk(crisis_override.get("min_safety"))

            boosted_urg = boost_urgency(urgency, min_urg)
            boosted_saf = boost_safety(safety_risk, min_saf)

            if boosted_urg != urgency:
                safeguard_reasons.append(
                    f"Crisis safeguard boosted urgency from {urgency} to {boosted_urg}"
                )
                urgency = boosted_urg

            if boosted_saf != safety_risk:
                safeguard_reasons.append(
                    f"Crisis safeguard boosted safety_risk from {safety_risk} to {boosted_saf}"
                )
                safety_risk = boosted_saf

            # Add crisis keyword reasons to rationale
            safeguard_reasons.extend(crisis_override.get("reasons", []))

        rationale = result.get("rationale", [])
        if safeguard_reasons:
            rationale = safeguard_reasons + rationale

        return {
            "urgency": urgency,
            "safety_risk": safety_risk,
            "incident_types": result.get("incident_types", []),
            "requires_human_review": result.get("requires_human_review", False),
            "escalation_recommended": urgency in ("critical", "high", "urgent"),
            "escalation_target": _escalation_target(urgency, safety_risk),
            "rationale": rationale,
        }


def _escalation_target(urgency: str, safety_risk: str) -> str | None:
    """Deterministic escalation target based on urgency/safety."""
    if urgency == "critical" or safety_risk == "immediate":
        return "emergency_response"
    if urgency == "high" or safety_risk == "high":
        return "human_case_worker"
    if urgency == "urgent":
        return "priority_support_queue"
    return None
