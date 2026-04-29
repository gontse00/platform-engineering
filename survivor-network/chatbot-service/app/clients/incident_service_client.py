"""Typed HTTP client for incident-service.

Used by chatbot-service to create operational cases and update timelines.
incident-service is the source of truth for case lifecycle.
"""

import logging
from typing import Any

import requests

from app.config.settings import settings
from app.logging_config import request_id_var

logger = logging.getLogger(__name__)


class IncidentServiceUnavailableError(Exception):
    pass


class IncidentServiceClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.incident_service_base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"X-Request-ID": request_id_var.get("-")}

    def create_case_from_intake(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create an operational case via POST /cases/from-intake.

        Expected payload keys:
            session_id, message, location_text, latitude, longitude,
            urgency, safety_risk, primary_need, secondary_needs,
            injury_status, immediate_danger, incident_type
        """
        try:
            response = requests.post(
                f"{self.base_url}/cases/from-intake",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("incident-service create_case_from_intake failed: %s", exc)
            raise IncidentServiceUnavailableError(str(exc)) from exc

    def update_case_status(self, case_id: str, status: str, reason: str | None = None) -> dict[str, Any]:
        """Update case status via PATCH /cases/{case_id}/status."""
        try:
            response = requests.patch(
                f"{self.base_url}/cases/{case_id}/status",
                json={"status": status, "reason": reason},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("incident-service update_case_status failed: %s", exc)
            raise IncidentServiceUnavailableError(str(exc)) from exc

    def add_timeline_entry(self, case_id: str, event_type: str, description: str, actor: str | None = None) -> dict[str, Any]:
        """Add timeline entry via POST /cases/{case_id}/timeline."""
        try:
            response = requests.post(
                f"{self.base_url}/cases/{case_id}/timeline",
                json={"event_type": event_type, "description": description, "actor": actor},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("incident-service add_timeline_entry failed: %s", exc)
            raise IncidentServiceUnavailableError(str(exc)) from exc
