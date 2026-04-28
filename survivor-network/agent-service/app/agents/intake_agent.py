"""Intake agent — extracts structured fields from survivor messages."""

import json
import logging
from typing import Any

from app.config import settings
from app.models import ConversationContext, ExtractedFields, SafetyFlags

logger = logging.getLogger(__name__)

INTAKE_SYSTEM_PROMPT = """\
You are an intake extraction engine for a crisis support platform.
Given a survivor's message and conversation context, extract structured fields.

Return valid JSON only:
{
  "primary_need": "Emergency Medical" | "Medication Access" | "Mental Health Support" | "Emergency Shelter" | "Protection Order Support" | "Transport" | null,
  "secondary_needs": [],
  "location": "string or null",
  "injury_status": "injured" | "not_injured" | null,
  "incident_summary": "brief summary or null",
  "safe_contact_method": "text" | "call" | "whatsapp" | "email" | null,
  "immediate_danger": true | false | null
}

Rules:
- Extract only what is clearly stated or strongly implied
- "I was beaten and I'm bleeding" implies injury_status=injured, primary_need=Emergency Medical
- "I am NOT injured" means injury_status=not_injured
- Use the conversation context to avoid re-extracting known fields
- Return null for fields you cannot determine
"""

# Keyword fallback for when LLM is unavailable
_NEED_KEYWORDS: dict[str, str] = {
    "bleed": "Emergency Medical", "injur": "Emergency Medical",
    "hospital": "Emergency Medical", "ambulance": "Emergency Medical",
    "medication": "Medication Access", "pills": "Medication Access",
    "counsel": "Mental Health Support", "trauma": "Mental Health Support",
    "mental": "Mental Health Support", "panic": "Mental Health Support",
    "shelter": "Emergency Shelter", "homeless": "Emergency Shelter",
    "nowhere to stay": "Emergency Shelter", "kicked me out": "Emergency Shelter",
    "legal": "Protection Order Support", "protection order": "Protection Order Support",
    "transport": "Transport", "stranded": "Transport",
}

_LOCATION_PATTERNS = [
    "i'm in ", "i am in ", "im in ", "we're in ", "we are in ",
    "i'm at ", "i am at ", "near ",
]

_INJURY_POSITIVE = ["bleeding", "injured", "hurt", "wound", "broken", "stab"]
_INJURY_NEGATIVE = ["not injured", "not hurt", "no injuries", "i'm fine"]

_CONTACT_KEYWORDS: dict[str, str] = {
    "whatsapp": "whatsapp", "text": "text", "sms": "text",
    "call me": "call", "phone": "call", "email": "email",
}


def _extract_fallback(message: str) -> dict[str, Any]:
    """Keyword-based extraction when LLM is unavailable."""
    lower = message.lower()
    fields: dict[str, Any] = {}

    for kw, need in _NEED_KEYWORDS.items():
        if kw in lower:
            fields["primary_need"] = need
            break

    for pattern in _LOCATION_PATTERNS:
        idx = lower.find(pattern)
        if idx >= 0:
            rest = message[idx + len(pattern):]
            for sep in [",", ".", "!", "\n", " and ", " but "]:
                si = rest.find(sep)
                if si > 0:
                    rest = rest[:si]
                    break
            loc = rest.strip()
            if 2 < len(loc) < 80:
                fields["location"] = loc
                break

    for phrase in _INJURY_NEGATIVE:
        if phrase in lower:
            fields["injury_status"] = "not_injured"
            break
    else:
        for kw in _INJURY_POSITIVE:
            if kw in lower:
                fields["injury_status"] = "injured"
                break

    for kw, method in _CONTACT_KEYWORDS.items():
        if kw in lower:
            fields["safe_contact_method"] = method
            break

    if len(message.strip()) > 20:
        fields["incident_summary"] = message.strip()[:200]

    return fields


def run_intake(
    message: str,
    context: ConversationContext,
    safety_flags: SafetyFlags,
    llm_client: Any | None = None,
) -> ExtractedFields:
    """Run intake extraction. Uses LLM if available, falls back to keywords."""

    if safety_flags.immediate_danger:
        base_fields = {"immediate_danger": True}
    else:
        base_fields = {}

    if llm_client is None:
        logger.info("LLM unavailable — using keyword extraction")
        extracted = _extract_fallback(message)
        extracted.update(base_fields)
        return ExtractedFields(**extracted)

    # Build LLM prompt with context
    context_block = ""
    if context.known_location:
        context_block += f"Known location: {context.known_location}\n"
    if context.known_primary_need:
        context_block += f"Known need: {context.known_primary_need}\n"
    if context.known_injury_status:
        context_block += f"Known injury: {context.known_injury_status}\n"

    user_content = f"Message: {message}"
    if context_block:
        user_content += f"\n\nAlready known:\n{context_block}"

    try:
        response = llm_client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=512,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content.strip()
        text = raw
        if text.startswith("```"):
            text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("```"))
        data = json.loads(text)
        data.update(base_fields)
        return ExtractedFields(**data)
    except Exception:
        logger.exception("LLM intake extraction failed, using fallback")
        extracted = _extract_fallback(message)
        extracted.update(base_fields)
        return ExtractedFields(**extracted)
