"""HTTP client for graph-core service.

Now supports passing pre-parsed intake data so graph-core can skip
redundant LLM intake parsing (reducing 4 LLM calls → 2).
"""

from typing import Any

import requests

from app.config.settings import settings
from app.logging_config import request_id_var


class GraphCoreUnavailableError(Exception):
    pass


class GraphCoreClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.graph_core_base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"X-Request-ID": request_id_var.get("-")}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise GraphCoreUnavailableError(str(exc)) from exc

    def _patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.patch(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise GraphCoreUnavailableError(str(exc)) from exc

    def assess_triage(
        self,
        message: str,
        top_k: int = 5,
        pre_parsed: dict[str, Any] | None = None,
        crisis_override: dict[str, Any] | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        """Call graph-core triage.

        Args:
            message: The enriched assessment message.
            top_k: Number of resource recommendations.
            pre_parsed: Pre-parsed intake fields from chatbot-service LLM.
                        If provided, graph-core skips its own intake LLM call.
                        Expected keys: location, primary_needs, barriers,
                                       immediate_danger, injury_status, incident_summary,
                                       latitude, longitude, location_accuracy, location_source
            crisis_override: Deterministic crisis safeguard data.
                             Keys: min_urgency, min_safety, reasons, immediate_danger
            latitude: GPS latitude from browser geolocation.
            longitude: GPS longitude from browser geolocation.
        """
        payload: dict[str, Any] = {"message": message, "top_k": top_k}
        if pre_parsed:
            payload["pre_parsed"] = pre_parsed
        if crisis_override:
            payload["crisis_override"] = crisis_override
        if latitude is not None and longitude is not None:
            payload["latitude"] = latitude
            payload["longitude"] = longitude
        return self._post("/triage/assess", payload)

    def create_case(
        self,
        message: str,
        top_k: int = 5,
        create_referrals: bool = True,
        pre_parsed: dict[str, Any] | None = None,
        crisis_override: dict[str, Any] | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": message,
            "top_k": top_k,
            "create_referrals": create_referrals,
        }
        if pre_parsed:
            payload["pre_parsed"] = pre_parsed
        if crisis_override:
            payload["crisis_override"] = crisis_override
        if latitude is not None and longitude is not None:
            payload["latitude"] = latitude
            payload["longitude"] = longitude
        return self._post("/cases/intake", payload)

    def update_case_context(
        self,
        case_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._patch(f"/cases/{case_id}/context", payload)
