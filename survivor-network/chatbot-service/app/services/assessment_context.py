"""Canonical assessment context DTO.

This is the single structured object that carries all assessment-relevant
data between chatbot-service and graph-core.  Both the message-time triage
call and the submit-time case-creation call use the same builder so the
context never diverges.
"""

from __future__ import annotations

from typing import Any


class AssessmentContext:
    """Immutable snapshot of session state for graph-core calls."""

    __slots__ = (
        "message",
        "pre_parsed",
        "crisis_override",
        "latitude",
        "longitude",
        "location_accuracy",
        "location_source",
    )

    def __init__(
        self,
        *,
        message: str,
        pre_parsed: dict[str, Any] | None = None,
        crisis_override: dict[str, Any] | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        location_accuracy: float | None = None,
        location_source: str | None = None,
    ) -> None:
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "pre_parsed", pre_parsed)
        object.__setattr__(self, "crisis_override", crisis_override)
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)
        object.__setattr__(self, "location_accuracy", location_accuracy)
        object.__setattr__(self, "location_source", location_source)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("AssessmentContext is immutable")

    # ------------------------------------------------------------------
    # Builder
    # ------------------------------------------------------------------

    @staticmethod
    def from_session_state(
        state: dict[str, Any],
        latest_message: str,
        crisis_override: dict[str, Any] | None = None,
    ) -> AssessmentContext:
        """Build a context object from the current session state.

        This is the ONE place that decides what gets sent to graph-core.
        Both the message pipeline and the submit pipeline call this.
        """
        pre_parsed = _build_pre_parsed(state)
        assessment_message = _build_assessment_message(state, latest_message)

        return AssessmentContext(
            message=assessment_message,
            pre_parsed=pre_parsed,
            crisis_override=crisis_override,
            latitude=state.get("latitude"),
            longitude=state.get("longitude"),
            location_accuracy=state.get("location_accuracy"),
            location_source=state.get("location_source"),
        )


# ------------------------------------------------------------------
# Helpers (module-private)
# ------------------------------------------------------------------


def _build_assessment_message(state: dict[str, Any], latest_message: str) -> str:
    """Build a rich context string for graph-core triage assessment."""
    parts: list[str] = []

    if state.get("incident_summary"):
        parts.append(state["incident_summary"])

    if state.get("location"):
        parts.append(f"Location: {state['location']}")

    if state.get("immediate_danger") is True:
        parts.append("User is in immediate danger")
    elif state.get("immediate_danger") is False:
        parts.append("User is not in immediate danger")

    if state.get("injury_status") == "injured":
        parts.append("User is injured")
    elif state.get("injury_status") == "not_injured":
        parts.append("User is not injured")

    if state.get("primary_need"):
        parts.append(f"Primary need: {state['primary_need']}")

    if state.get("safe_contact_method"):
        parts.append(f"Safe contact method: {state['safe_contact_method']}")

    parts.append(f"Latest user message: {latest_message}")

    return ". ".join(parts)


def _build_pre_parsed(state: dict[str, Any]) -> dict[str, Any]:
    """Build the pre_parsed payload from current session state.

    This data is sent to graph-core so it can skip its own intake LLM call.
    """
    pre_parsed: dict[str, Any] = {}

    if state.get("location"):
        pre_parsed["location"] = state["location"]

    if state.get("primary_need"):
        pre_parsed["primary_needs"] = [state["primary_need"]]
    else:
        pre_parsed["primary_needs"] = []

    pre_parsed["barriers"] = []

    if state.get("immediate_danger") is not None:
        pre_parsed["immediate_danger"] = state["immediate_danger"]

    if state.get("injury_status"):
        pre_parsed["injury_status"] = state["injury_status"]

    if state.get("incident_summary"):
        pre_parsed["incident_summary"] = state["incident_summary"]

    if state.get("latitude") is not None:
        pre_parsed["latitude"] = state["latitude"]
        pre_parsed["longitude"] = state["longitude"]
        pre_parsed["location_accuracy"] = state.get("location_accuracy", 0.0)
        pre_parsed["location_source"] = state.get("location_source", "browser")

    return pre_parsed
