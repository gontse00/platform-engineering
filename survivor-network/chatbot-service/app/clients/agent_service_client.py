"""Typed HTTP client for agent-service."""

import logging
from typing import Any

import requests

from app.config.settings import settings

logger = logging.getLogger(__name__)


class AgentServiceUnavailableError(Exception):
    pass


class AgentServiceClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.agent_service_base_url).rstrip("/")

    def reason(
        self,
        session_id: str,
        message: str,
        conversation_context: dict[str, Any] | None = None,
        safety_flags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call POST /reason on agent-service.

        Returns the full ReasonResponse as a dict.
        Raises AgentServiceUnavailableError on any failure.
        """
        payload = {
            "session_id": session_id,
            "message": message,
            "conversation_context": conversation_context or {},
            "safety_flags": safety_flags or {},
        }

        try:
            response = requests.post(
                f"{self.base_url}/reason",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("agent-service call failed: %s", exc)
            raise AgentServiceUnavailableError(str(exc)) from exc


# Safe fallback when agent-service is unavailable
AGENT_FALLBACK_RESPONSE: dict[str, Any] = {
    "extracted": {
        "primary_need": None,
        "secondary_needs": [],
        "location": None,
        "injury_status": None,
        "incident_summary": None,
        "safe_contact_method": None,
        "immediate_danger": None,
    },
    "triage": {
        "suggested_urgency": "standard",
        "safety_risk": "low",
        "requires_escalation": False,
        "rationale": ["agent-service unavailable — using safe defaults"],
    },
    "actions": [],
    "reply": {
        "message": "I've noted what you shared. Can you tell me more about where you are and whether you're safe right now?",
    },
}
