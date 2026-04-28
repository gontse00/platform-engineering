"""Safe HTTP helpers for service-to-service calls."""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_timeout = httpx.Timeout(settings.request_timeout_seconds)


async def safe_get_json(url: str, params: dict | None = None) -> tuple[dict | None, str | None]:
    """GET with safe error handling. Returns (data, error_message)."""
    try:
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json(), None
    except Exception as exc:
        logger.error("GET %s failed: %s", url, exc)
        return None, str(exc)


async def safe_post_json(url: str, json: dict | None = None) -> tuple[dict | None, str | None]:
    """POST with safe error handling. Returns (data, error_message)."""
    try:
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.post(url, json=json or {})
            resp.raise_for_status()
            return resp.json(), None
    except Exception as exc:
        logger.error("POST %s failed: %s", url, exc)
        return None, str(exc)


async def safe_patch_json(url: str, json: dict | None = None) -> tuple[dict | None, str | None]:
    """PATCH with safe error handling. Returns (data, error_message)."""
    try:
        async with httpx.AsyncClient(timeout=_timeout) as client:
            resp = await client.patch(url, json=json or {})
            resp.raise_for_status()
            return resp.json(), None
    except Exception as exc:
        logger.error("PATCH %s failed: %s", url, exc)
        return None, str(exc)


async def check_health(url: str) -> str:
    """Check /health of a service. Returns 'ok' or 'unavailable'."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3)) as client:
            resp = await client.get(f"{url}/health")
            return "ok" if resp.status_code == 200 else "unavailable"
    except Exception:
        return "unavailable"
