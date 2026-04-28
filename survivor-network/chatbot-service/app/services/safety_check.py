"""Deterministic safety layer — runs before any agent/LLM call.

Rule-based, explicit, testable. No LLM dependency.
Produces structured safety flags for agent-service.
"""

from app.domain.constants import check_crisis_keywords, Urgency


def run_safety_check(message: str) -> dict:
    """Scan message for crisis keywords and produce safety flags.

    Returns:
        {
            "immediate_danger": bool,
            "urgency_floor": str,  # "standard" | "urgent" | "high" | "critical"
            "matched_keywords": [str, ...]
        }
    """
    result = check_crisis_keywords(message)

    if result is None:
        return {
            "immediate_danger": False,
            "urgency_floor": "standard",
            "matched_keywords": [],
        }

    # Convert enum to string for serialization
    urgency = result["min_urgency"]
    urgency_str = urgency.value if isinstance(urgency, Urgency) else str(urgency)

    return {
        "immediate_danger": result.get("immediate_danger", False),
        "urgency_floor": urgency_str,
        "matched_keywords": result.get("reasons", []),
    }
