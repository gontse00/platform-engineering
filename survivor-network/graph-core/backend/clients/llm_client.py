"""LLM client for graph-core: triage assessment only.

Previously had 3 LLM methods (parse_intake, assess_triage, assess_escalation).
Now reduced to 1:
- parse_intake → replaced by pre-parsed data from chatbot-service
- assess_escalation → replaced by deterministic rules in domain/constants.py
- assess_triage → KEPT (urgency + safety scoring still benefits from LLM)

Hardened with Pydantic validation, enum normalization, timeout, retry.
"""

import json
import logging
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, field_validator

from config.settings import settings
from domain.constants import normalize_urgency, normalize_safety_risk

logger = logging.getLogger(__name__)


TRIAGE_SYSTEM_PROMPT = """\
You are a triage assessment engine for a crisis support platform.
Given a message from someone in distress and their parsed intake data, assess the urgency and risk.

You must return valid JSON with this exact structure:
{
  "urgency": "critical" | "high" | "urgent" | "standard",
  "safety_risk": "immediate" | "high" | "medium" | "low",
  "incident_types": ["list of incident types detected"],
  "requires_human_review": true/false,
  "rationale": ["list of reasons for the assessment"]
}

Urgency levels:
- "critical": Life-threatening situation right now (active bleeding, unconscious, not breathing, severe injury, heart attack, stroke, active violence happening NOW)
- "high": Serious safety threat (assault, domestic violence, trafficking, child in danger, active threats, abusive partner)
- "urgent": Needs prompt attention (needs shelter tonight, out of medication, panic, trauma, protection order needed, mental health crisis)
- "standard": Non-emergency support request

Safety risk levels:
- "immediate": Person is in danger RIGHT NOW
- "high": Person has been harmed or is at significant risk
- "medium": Person is distressed but not in immediate physical danger
- "low": Person is safe but needs support

Incident types (detect all that apply):
- "Assault", "Domestic Violence", "Displacement", "Missing Medication",
  "Child Endangerment", "Threats", "Sexual Violence", "Trafficking",
  "Robbery", "Stalking", "Workplace Violence"

Rules:
- Assess SEVERITY, not just keywords. "I'm bleeding from a paper cut" is standard, not critical. "I'm bleeding heavily and feeling dizzy" IS critical.
- Consider temporal context: "I was attacked last week" (high, not critical) vs "I'm being attacked right now" (critical).
- Multiple risk factors compound: domestic violence + injury + no safe place = critical even if no single factor is critical alone.
- When in doubt, err on the side of higher urgency — false negatives are more dangerous than false positives.
- Return only the JSON, no other text.
"""


class TriageResult(BaseModel):
    """Validated triage assessment from LLM."""
    urgency: str = "standard"
    safety_risk: str = "low"
    incident_types: list[str] = []
    requires_human_review: bool = False
    rationale: list[str] = []

    @field_validator("urgency", mode="before")
    @classmethod
    def _norm_urgency(cls, v: Any) -> str:
        return normalize_urgency(v if isinstance(v, str) else None)

    @field_validator("safety_risk", mode="before")
    @classmethod
    def _norm_safety(cls, v: Any) -> str:
        return normalize_safety_risk(v if isinstance(v, str) else None)

    @field_validator("incident_types", mode="before")
    @classmethod
    def _ensure_list(cls, v: Any) -> list:
        if isinstance(v, list):
            return [str(x) for x in v]
        return []


TRIAGE_DEFAULT = TriageResult(
    rationale=["LLM assessment unavailable — defaulting to standard"],
)


class GraphCoreLLMClient:
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

    def assess_triage(self, message: str, intake_data: dict[str, Any]) -> dict[str, Any]:
        """Assess urgency, risk, and incident types via LLM.

        Returns validated dict with normalized enum values.
        """
        if not self.available:
            logger.warning("LLM unavailable for triage — using defaults")
            return TRIAGE_DEFAULT.model_dump()

        user_content = f"Message: {message}\n\nParsed intake data: {json.dumps(intake_data)}"

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=1024,
                temperature=settings.llm_temperature,
                messages=[
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )

            raw_text = response.choices[0].message.content.strip()
            return self._parse_and_validate(raw_text).model_dump()

        except (APITimeoutError, RateLimitError) as exc:
            logger.error("OpenAI transient error in triage: %s", type(exc).__name__)
            return TRIAGE_DEFAULT.model_dump()
        except APIError as exc:
            logger.error("OpenAI API error in triage: status=%s", getattr(exc, "status_code", "unknown"))
            return TRIAGE_DEFAULT.model_dump()
        except Exception:
            logger.exception("LLM triage assessment failed")
            return TRIAGE_DEFAULT.model_dump()

    @staticmethod
    def _parse_and_validate(raw_text: str) -> TriageResult:
        """Parse JSON from LLM response and validate through Pydantic."""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            return TriageResult.model_validate(data)
        except (json.JSONDecodeError, Exception):
            logger.warning("Failed to parse LLM triage response, using defaults")
            return TRIAGE_DEFAULT
