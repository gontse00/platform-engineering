from typing import Any
import requests

from app.config.settings import settings


class GraphCoreUnavailableError(Exception):
    pass


class GraphCoreClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.graph_core_base_url).rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
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
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise GraphCoreUnavailableError(str(exc)) from exc

    def assess_triage(self, message: str, top_k: int = 5) -> dict[str, Any]:
        return self._post("/triage/assess", {"message": message, "top_k": top_k})

    def create_case(self, message: str, top_k: int = 5, create_referrals: bool = True) -> dict[str, Any]:
        return self._post(
            "/cases/intake",
            {
                "message": message,
                "top_k": top_k,
                "create_referrals": create_referrals,
            },
        )

    def update_case_context(
        self,
        case_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._patch(f"/cases/{case_id}/context", payload)