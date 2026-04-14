"""Thin wrapper around the OpenAI SDK for structured crisis-intake conversations.

Hardened with:
- Schema validation via Pydantic
- Enum normalization for extracted fields
- Retry with exponential backoff
- Configurable timeout
- LLM kill-switch (settings.llm_enabled)
- Safe logging (no PII in logs)
"""

import json
import logging
import random
import time
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, field_validator

from app.config.settings import settings
from app.domain.constants import (
    check_crisis_keywords,
    normalize_contact_method,
    normalize_injury_status,
    normalize_primary_need,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a crisis-intake assistant for an emergency support platform called Survivor Network.
Your role is to have a calm, empathetic conversation with someone who may be in danger or distress,
and to extract structured information that will help route them to the right support services.

You must extract the following fields from the conversation. Do NOT ask for all of them at once —
ask naturally, one or two at a time, based on what the person has already shared.

Required fields:
- incident_summary: A brief description of what happened to them
- location: Where they are right now (city, area, or address — anywhere in the world)
- immediate_danger: Whether they are currently in immediate danger (true/false)
- injury_status: Whether they are injured ("injured", "not_injured", or null if unknown)
- primary_need: Their most urgent need. Must be one of: "Emergency Medical", "Medication Access",
  "Mental Health Support", "Emergency Shelter", "Protection Order Support", "Transport"
- safe_contact_method: Safest way to reach them ("text", "call", "whatsapp", "email", or other)

Guidelines:
- Be warm but concise. This person may be in crisis — do not waste their time.
- If someone describes a situation that clearly implies a field value, extract it without asking again.
  For example, "I was beaten and I'm bleeding" implies injury_status=injured and likely primary_need=Emergency Medical.
- Handle negation carefully: "I am NOT injured" means injury_status=not_injured.
- If someone mentions multiple needs, pick the most urgent as primary_need.
- Never judge, question their story, or minimize their experience.
- If information is ambiguous, ask a brief clarifying question.
- Always prioritize safety — if they mention active danger, acknowledge it immediately.

You must respond with valid JSON only, with this exact structure:
{
  "bot_message": "Your empathetic response and/or follow-up question",
  "extracted_fields": {
    "incident_summary": "string or null",
    "location": "string or null",
    "immediate_danger": true/false/null,
    "injury_status": "injured"/"not_injured"/null,
    "primary_need": "one of the allowed values or null",
    "safe_contact_method": "text"/"call"/"whatsapp"/"email"/null
  }
}

Only include fields in extracted_fields that you can confidently determine from THIS message combined
with prior conversation context. Use null for fields you cannot yet determine.
Respond ONLY with the JSON object, no other text.
"""


class ExtractedFields(BaseModel):
    """Pydantic model for validated LLM-extracted fields."""
    incident_summary: str | None = None
    location: str | None = None
    immediate_danger: bool | None = None
    injury_status: str | None = None
    primary_need: str | None = None
    safe_contact_method: str | None = None

    @field_validator("injury_status", mode="before")
    @classmethod
    def _normalize_injury(cls, v: Any) -> str | None:
        if isinstance(v, str):
            return normalize_injury_status(v)
        return None

    @field_validator("primary_need", mode="before")
    @classmethod
    def _normalize_need(cls, v: Any) -> str | None:
        if isinstance(v, str):
            return normalize_primary_need(v)
        return None

    @field_validator("safe_contact_method", mode="before")
    @classmethod
    def _normalize_contact(cls, v: Any) -> str | None:
        if isinstance(v, str):
            return normalize_contact_method(v)
        return None

    @field_validator("immediate_danger", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> bool | None:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lower = v.lower().strip()
            if lower in ("true", "yes", "1"):
                return True
            if lower in ("false", "no", "0"):
                return False
        return None


class LLMResponse(BaseModel):
    """Validated LLM response shape."""
    bot_message: str = ""
    extracted_fields: ExtractedFields = ExtractedFields()


FALLBACK_OPENING = (
    "I'm here to help. You're safe to share what's happening, "
    "and I'll do my best to connect you with the right support."
)

FALLBACK_ERROR = (
    "I've noted what you shared. "
    "Can you tell me more about where you are and whether you're safe right now?"
)


# ---------------------------------------------------------------------------
# Keyword-based field extraction (used when LLM is disabled)
# ---------------------------------------------------------------------------

_NEED_KEYWORDS: dict[str, str] = {
    "bleed": "Emergency Medical",
    "injur": "Emergency Medical",
    "hospital": "Emergency Medical",
    "ambulance": "Emergency Medical",
    "medic": "Emergency Medical",
    "unconscious": "Emergency Medical",
    "collapsed": "Emergency Medical",
    "medication": "Medication Access",
    "prescription": "Medication Access",
    "pills": "Medication Access",
    "hiv": "Medication Access",
    "arv": "Medication Access",
    "counsel": "Mental Health Support",
    "trauma": "Mental Health Support",
    "anxiety": "Mental Health Support",
    "depress": "Mental Health Support",
    "mental": "Mental Health Support",
    "panic": "Mental Health Support",
    "shelter": "Emergency Shelter",
    "homeless": "Emergency Shelter",
    "nowhere to stay": "Emergency Shelter",
    "kicked me out": "Emergency Shelter",
    "safe place": "Emergency Shelter",
    "nowhere to go": "Emergency Shelter",
    "legal": "Protection Order Support",
    "protection order": "Protection Order Support",
    "restraining": "Protection Order Support",
    "court": "Protection Order Support",
    "saps": "Protection Order Support",
    "transport": "Transport",
    "ride": "Transport",
    "stranded": "Transport",
    "no taxi": "Transport",
}

_LOCATION_PATTERNS: list[str] = [
    "i'm in ", "i am in ", "im in ", "we're in ", "we are in ",
    "i'm at ", "i am at ", "located in ", "near ",
]

_INJURY_POSITIVE = ["bleeding", "injured", "hurt", "wound", "broken", "bruise", "cut", "stab"]
_INJURY_NEGATIVE = ["not injured", "not hurt", "no injuries", "i'm fine", "i am fine", "not bleeding"]

_CONTACT_KEYWORDS: dict[str, str] = {
    "whatsapp": "whatsapp",
    "text": "text",
    "sms": "text",
    "call me": "call",
    "phone": "call",
    "email": "email",
}

_DANGER_POSITIVE = [
    "being attacked", "attacking me", "hitting me", "beating me",
    "he is here", "she is here", "in danger", "not safe",
    "right now", "help me", "please hurry",
]
_DANGER_NEGATIVE = [
    "not in danger", "i'm safe", "i am safe", "safe right now",
    "not in immediate", "safe for now",
]


def _extract_fields_from_text(message: str) -> dict[str, Any]:
    """Keyword-based field extraction — no LLM needed."""
    lower = message.lower()
    fields: dict[str, Any] = {}

    # Primary need
    for keyword, need in _NEED_KEYWORDS.items():
        if keyword in lower:
            fields["primary_need"] = need
            break

    # Location — grab text after location indicators
    for pattern in _LOCATION_PATTERNS:
        idx = lower.find(pattern)
        if idx >= 0:
            rest = message[idx + len(pattern):]
            # Take until comma, period, or end of sentence
            for sep in [",", ".", "!", "\n", " and ", " but ", " with "]:
                sep_idx = rest.find(sep)
                if sep_idx > 0:
                    rest = rest[:sep_idx]
                    break
            location = rest.strip()
            if 2 < len(location) < 80:
                fields["location"] = location
                break

    # Injury status
    for phrase in _INJURY_NEGATIVE:
        if phrase in lower:
            fields["injury_status"] = "not_injured"
            break
    else:
        for keyword in _INJURY_POSITIVE:
            if keyword in lower:
                fields["injury_status"] = "injured"
                break

    # Immediate danger
    for phrase in _DANGER_NEGATIVE:
        if phrase in lower:
            fields["immediate_danger"] = False
            break
    else:
        for phrase in _DANGER_POSITIVE:
            if phrase in lower:
                fields["immediate_danger"] = True
                break

    # Contact method
    for keyword, method in _CONTACT_KEYWORDS.items():
        if keyword in lower:
            fields["safe_contact_method"] = method
            break

    # Incident summary — use the message itself if it's substantial enough
    if len(message.strip()) > 20:
        fields["incident_summary"] = message.strip()[:200]

    return fields


_MOCK_RESPONSES = [
    "Thank you for sharing that. I want to make sure we get you the right help. Are you in a safe place right now?",
    "I hear you, and I'm here to help. Can you tell me where you are so we can find support near you?",
    "That sounds really difficult. Your safety matters most. Are you injured?",
    "I've noted everything you've shared. What's the safest way for someone to reach you — text, call, or WhatsApp?",
    "Thank you for trusting us with this. We're working on connecting you with support. Is there anything else you need right now?",
]


class LLMClient:
    def __init__(self) -> None:
        if settings.llm_enabled and settings.openai_api_key:
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.llm_timeout,
                max_retries=settings.llm_max_retries,
            )
        else:
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None and settings.llm_enabled

    def process_message(
        self,
        conversation_history: list[dict[str, str]],
        current_state: dict[str, Any],
        user_message: str = "",
    ) -> dict[str, Any]:
        """Send conversation to LLM for response + field extraction.

        Returns dict with keys: bot_message, extracted_fields, crisis_override
        """
        # 1. Deterministic crisis safeguard — runs BEFORE LLM
        crisis = check_crisis_keywords(user_message) if user_message else None

        # 2. LLM call (if available)
        if not self.available:
            logger.info("LLM disabled — using keyword extraction")
            extracted = _extract_fields_from_text(user_message)

            # Crisis safeguard overrides
            if crisis and crisis.get("immediate_danger"):
                extracted["immediate_danger"] = True

            bot_message = random.choice(_MOCK_RESPONSES)
            return {
                "bot_message": bot_message,
                "extracted_fields": extracted,
                "crisis_override": crisis,
            }

        state_context = self._build_state_context(current_state)
        messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + state_context}]

        for msg in conversation_history:
            role = msg.get("role", "")
            if role not in ("user", "assistant"):
                continue
            messages.append({"role": role, "content": msg["content"]})

        if len(messages) == 1:
            messages.append({"role": "user", "content": "(Session just started — greet the user.)"})

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=1024,
                temperature=settings.llm_temperature,
                messages=messages,
            )

            raw_text = response.choices[0].message.content.strip()
            parsed = self._parse_and_validate(raw_text)

            result = {
                "bot_message": parsed.bot_message,
                "extracted_fields": parsed.extracted_fields.model_dump(exclude_none=True),
                "crisis_override": crisis,
            }

            # Crisis safeguard: force immediate_danger if critical keywords detected
            if crisis and crisis.get("immediate_danger"):
                result["extracted_fields"]["immediate_danger"] = True

            return result

        except (APITimeoutError, RateLimitError) as exc:
            logger.error("OpenAI transient error: %s", type(exc).__name__)
            return {
                "bot_message": FALLBACK_ERROR,
                "extracted_fields": {"immediate_danger": True} if crisis and crisis.get("immediate_danger") else {},
                "crisis_override": crisis,
            }
        except APIError as exc:
            logger.error("OpenAI API error: status=%s", getattr(exc, "status_code", "unknown"))
            return {
                "bot_message": FALLBACK_ERROR,
                "extracted_fields": {"immediate_danger": True} if crisis and crisis.get("immediate_danger") else {},
                "crisis_override": crisis,
            }
        except Exception:
            logger.exception("LLM processing failed unexpectedly")
            return {
                "bot_message": FALLBACK_ERROR,
                "extracted_fields": {"immediate_danger": True} if crisis and crisis.get("immediate_danger") else {},
                "crisis_override": crisis,
            }

    def generate_opening(self) -> str:
        """Generate an empathetic opening message for a new session."""
        if not self.available:
            return FALLBACK_OPENING

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=256,
                temperature=settings.llm_temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": "(New session started. Generate a warm, brief opening message. Respond with JSON as specified.)",
                    },
                ],
            )

            raw_text = response.choices[0].message.content.strip()
            parsed = self._parse_and_validate(raw_text)
            return parsed.bot_message or FALLBACK_OPENING

        except Exception:
            logger.exception("Failed to generate opening message")
            return FALLBACK_OPENING

    def _build_state_context(self, state: dict[str, Any]) -> str:
        """Build a context block showing what we already know."""
        collected = {}
        for field in [
            "incident_summary", "location", "immediate_danger",
            "injury_status", "primary_need", "safe_contact_method",
        ]:
            value = state.get(field)
            if value is not None:
                collected[field] = value

        missing = [
            f for f in [
                "incident_summary", "location", "immediate_danger",
                "injury_status", "primary_need", "safe_contact_method",
            ]
            if state.get(f) is None
        ]

        parts = ["Current intake state:"]
        if collected:
            parts.append(f"Already collected: {json.dumps(collected)}")
        if missing:
            parts.append(f"Still needed: {', '.join(missing)}")
        else:
            parts.append("All required fields have been collected. Let the user know they can submit their case.")

        assessment = state.get("latest_graph_assessment")
        if assessment:
            triage = assessment.get("triage", {})
            if triage.get("urgency"):
                parts.append(f"Current triage urgency: {triage['urgency']}")
            if triage.get("safety_risk"):
                parts.append(f"Safety risk level: {triage['safety_risk']}")

        return "\n".join(parts)

    @staticmethod
    def _parse_and_validate(raw_text: str) -> LLMResponse:
        """Parse LLM JSON response and validate through Pydantic model."""
        text = raw_text
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            return LLMResponse.model_validate(data)
        except (json.JSONDecodeError, Exception):
            # If JSON parsing fails, treat the whole text as the bot message
            return LLMResponse(bot_message=raw_text, extracted_fields=ExtractedFields())
