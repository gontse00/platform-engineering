"""Graph-core domain constants, enums, and deterministic escalation rules."""

from __future__ import annotations

ALLOWED_NODE_TYPES = {
    # core operational
    "Survivor",
    "Case",
    "Helper",
    "Organization",
    "Location",

    # need taxonomy
    "NeedCategory",
    "NeedType",
    "UrgencyLevel",

    # service/resource taxonomy
    "Resource",
    "ResourceType",
    "ServiceType",

    # context layer
    "Incident",
    "IncidentType",
    "RiskFactor",
    "Barrier",
    "Assessment",
    "Referral",

    # state/time layer
    "Status",
    "AvailabilityWindow",
    "Priority",
    "CaseStage",
}


ALLOWED_EDGE_TYPES = {
    # core case relationships
    "INVOLVED_IN",
    "LOCATED_IN",
    "TRIGGERED_BY",
    "EXPERIENCED",

    # need relationships
    "HAS_NEED",
    "IS_A",
    "HAS_URGENCY",
    "REQUIRES",

    # service/resource relationships
    "INSTANCE_OF",
    "PROVIDES",
    "SPECIALIZES_IN",
    "OPERATED_BY",
    "AVAILABLE_AT",

    # context/barrier/risk
    "HAS_RISK",
    "BLOCKED_BY",
    "IMPACTS",
    "ASSESSED_AS",

    # helper/referral
    "CAN_SUPPORT",
    "ASSIGNED_TO",
    "REFERRED_TO",
    "FOR_CASE",
    "TO_RESOURCE",

    # status/time
    "HAS_STATUS",
    "AVAILABLE_DURING",
    "UPDATED_TO",
}


# ---------------------------------------------------------------------------
# Canonical enum values (mirrored from chatbot-service for consistency)
# ---------------------------------------------------------------------------

VALID_URGENCY = {"critical", "high", "urgent", "standard"}
VALID_SAFETY_RISK = {"immediate", "high", "medium", "low"}
VALID_ESCALATION_QUEUES = {"emergency_response", "human_case_worker", "priority_support_queue"}

URGENCY_ORDER = ["standard", "urgent", "high", "critical"]
SAFETY_ORDER = ["low", "medium", "high", "immediate"]


def normalize_urgency(value: str | None) -> str:
    if not value:
        return "standard"
    v = value.lower().strip()
    return v if v in VALID_URGENCY else "standard"


def normalize_safety_risk(value: str | None) -> str:
    if not value:
        return "low"
    v = value.lower().strip()
    return v if v in VALID_SAFETY_RISK else "low"


def urgency_gte(a: str, b: str) -> bool:
    """Return True if urgency `a` is >= urgency `b`."""
    return URGENCY_ORDER.index(a) >= URGENCY_ORDER.index(b)


def safety_gte(a: str, b: str) -> bool:
    """Return True if safety risk `a` is >= safety risk `b`."""
    return SAFETY_ORDER.index(a) >= SAFETY_ORDER.index(b)


def boost_urgency(current: str, minimum: str) -> str:
    """Return the higher of two urgency levels."""
    if URGENCY_ORDER.index(minimum) > URGENCY_ORDER.index(current):
        return minimum
    return current


def boost_safety(current: str, minimum: str) -> str:
    """Return the higher of two safety risk levels."""
    if SAFETY_ORDER.index(minimum) > SAFETY_ORDER.index(current):
        return minimum
    return current


# ---------------------------------------------------------------------------
# Deterministic escalation rules — replaces the LLM escalation call
# ---------------------------------------------------------------------------

def determine_escalation(urgency: str, safety_risk: str) -> dict:
    """Pure rule-based escalation. No LLM needed.

    Rules:
    - critical urgency OR immediate safety → emergency_response, handoff required
    - high urgency OR high safety → human_case_worker, handoff required
    - urgent urgency → priority_support_queue
    - standard → no escalation
    """
    if urgency == "critical" or safety_risk == "immediate":
        return {
            "escalate": True,
            "level": "critical",
            "queue": "emergency_response",
            "handoff_required": True,
            "actions": [
                {
                    "action": "Route to emergency response team immediately",
                    "target": "emergency_response",
                    "priority": "critical",
                    "reason": f"Urgency: {urgency}, Safety risk: {safety_risk}",
                }
            ],
        }

    if urgency == "high" or safety_risk == "high":
        return {
            "escalate": True,
            "level": "high",
            "queue": "human_case_worker",
            "handoff_required": True,
            "actions": [
                {
                    "action": "Assign to human case worker for immediate review",
                    "target": "human_case_worker",
                    "priority": "high",
                    "reason": f"Urgency: {urgency}, Safety risk: {safety_risk}",
                }
            ],
        }

    if urgency == "urgent":
        return {
            "escalate": True,
            "level": "urgent",
            "queue": "priority_support_queue",
            "handoff_required": False,
            "actions": [
                {
                    "action": "Add to priority support queue",
                    "target": "priority_support_queue",
                    "priority": "urgent",
                    "reason": f"Urgency: {urgency}, Safety risk: {safety_risk}",
                }
            ],
        }

    # standard
    return {
        "escalate": False,
        "level": "none",
        "queue": None,
        "handoff_required": False,
        "actions": [],
    }
