"""Configurable LLM provider abstraction."""

import logging

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_initialized = False


def get_llm_client() -> OpenAI | None:
    """Return an OpenAI client if LLM is enabled and configured, else None."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not settings.llm_enabled:
        logger.info("LLM disabled via config")
        return None

    if not settings.openai_api_key:
        logger.warning("No OPENAI_API_KEY set — LLM unavailable")
        return None

    _client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )
    logger.info("LLM client initialized (model=%s)", settings.openai_model)
    return _client
