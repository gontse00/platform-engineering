"""Triage agent — assesses urgency and safety risk."""

import json
import logging
from typing import Any

from app.config import settings
from app.models import ExtractedFields, SafetyFlags, TriageResult

logger = logging.getLogger(__name__)

TRIAGE_SYSTEM_PROMPT = """\
You are a triage engine for a crisis support platform.
Given extracted intake fields and safety flags, assess urgency and risk.

Return valid JSON:
{
  "suggested_urgency": "critical" | "high" | "urgent" | "standard",
  "safety_risk": "immediate" | "high" | "medium" | "low",
  "requires_escalation": true | false,
  "rationale": ["reason1", "reason2"]
}

Rules:
- critical: life-threatening right now (active bleeding, violence, overdose)
- high: serious threat (assault, DV, armed threat, child danger)
- urgent: needs prompt attention (shelter tonight, missing meds, panic)
- standard: non-emergency support
- If safety_flags.urgency_floor is set, your suggested_urgency must be >= that floor
- Multiple risk factors compound
- When in doubt, err toward higher urgency
"""

URGENCY_ORDER = ["standard", "urgent", "high", "critical"]
SAFETY_ORDER = ["low", "medium", "high", "immediate"]

# Keyword-based triage fallback
_CRITICAL = ["bleeding", "stabbed", "unconscious", "overdose", "being attacked",
             "kill myself", "want to die", "collapsed", "choking", "not breathing"]
_HIGH = ["raped", "sexual assault", "death threat", "kill me", "knife", "gun",
         "weapon", "child in danger", "kidnapped", "locked in", "trapped", "beaten"]
_URGENT = ["shelter", "nowhere to stay", "medication", "panic", "protection order",
           "kicked me out", "mental health", "trauma", "afraid"]

_INCIDENT_MAP: dict[str, str] = {
    "assault": "Assault", "beaten": "Assault", "stabbed": "Assault",
    "attacked": "Assault", "domestic": "Domestic Violence",
    "raped": "Sexual Violence", "sexual": "Sexual Violence",
    "medication": "Missing Medication", "child": "Child Endangerment",
    "threat": "Threats", "kill me": "Threats",
}


def _triage_fallback(message: str, extracted: ExtractedFields, safety_flags: SafetyFlags) -> TriageResult:
    """Keyword-based triage when LLM is unavailable."""
    lower = message.lower()
    urgency, safety_risk, rationale = "standard", "low", []

    for kw in _CRITICAL:
        if kw in lower:
            urgency, safety_risk = "critical", "immediate"
            rationale.append(f"Critical keyword: '{kw}'")
            break

    if urgency == "standard":
        for kw in _HIGH:
            if kw in lower:
                urgency, safety_risk = "high", "high"
                rationale.append(f"High-risk keyword: '{kw}'")
                break

    if urgency == "standard":
        for kw in _URGENT:
            if kw in lower:
                urgency, safety_risk = "urgent", "medium"
                rationale.append(f"Urgent keyword: '{kw}'")
                break

    # Apply urgency floor from safety flags
    floor = safety_flags.urgency_floor
    if URGENCY_ORDER.index(floor) > URGENCY_ORDER.index(urgency):
        rationale.append(f"Urgency raised to floor: {floor}")
        urgency = floor

    if not rationale:
        rationale.append("No crisis keywords detected")

    requires_escalation = urgency in ("critical", "high")

    return TriageResult(
        suggested_urgency=urgency,
        safety_risk=safety_risk,
        requires_escalation=requires_escalation,
        rationale=rationale,
    )


def run_triage(
    message: str,
    extracted: ExtractedFields,
    safety_flags: SafetyFlags,
    llm_client: Any | None = None,
) -> TriageResult:
    """Run triage assessment. Uses LLM if available, falls back to keywords."""

    if llm_client is None:
        logger.info("LLM unavailable — using keyword triage")
        return _triage_fallback(message, extracted, safety_flags)

    user_content = json.dumps({
        "message": message,
        "extracted": extracted.model_dump(),
        "safety_flags": safety_flags.model_dump(),
    })

    try:
        response = llm_client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=512,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content.strip()
        text = raw
        if text.startswith("```"):
            text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("```"))
        data = json.loads(text)

        # Enforce urgency floor
        suggested = data.get("suggested_urgency", "standard")
        floor = safety_flags.urgency_floor
        if URGENCY_ORDER.index(floor) > URGENCY_ORDER.index(suggested):
            data["rationale"] = data.get("rationale", [])
            data["rationale"].insert(0, f"Urgency raised from {suggested} to floor: {floor}")
            data["suggested_urgency"] = floor

        return TriageResult(**data)
    except Exception:
        logger.exception("LLM triage failed, using fallback")
        return _triage_fallback(message, extracted, safety_flags)
