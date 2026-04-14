from typing import Any


REQUIRED_FIELDS = [
    "incident_summary",
    "location",
    "immediate_danger",
    "injury_status",
    "primary_need",
    "safe_contact_method",
]


class IntakeStateService:
    @staticmethod
    def initial_state() -> dict[str, Any]:
        return {
            "incident_summary": None,
            "location": None,
            "immediate_danger": None,
            "injury_status": None,
            "primary_need": None,
            "safe_contact_method": None,
            "latitude": None,
            "longitude": None,
            "location_accuracy": None,
            "location_source": None,
            "attachments": [],
            "history": [],
            "latest_graph_assessment": None,
            "submission_mode": None,
        }

    @staticmethod
    def apply_user_message(
        state: dict[str, Any],
        message: str,
        llm_extracted: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update state with user message and LLM-extracted fields.

        Args:
            state: Current intake state dict.
            message: Raw user message text.
            llm_extracted: Fields extracted by the LLM from this message.
                           Keys match REQUIRED_FIELDS, values are the extracted data or None.
        """
        updated = dict(state)
        updated["history"] = list(updated.get("history", []))
        updated["history"].append({"role": "user", "content": message})

        if llm_extracted:
            for field in REQUIRED_FIELDS:
                new_value = llm_extracted.get(field)
                if new_value is not None and updated.get(field) is None:
                    updated[field] = new_value

        return updated

    @staticmethod
    def apply_bot_message(state: dict[str, Any], message: str) -> dict[str, Any]:
        """Append a bot message to the conversation history."""
        updated = dict(state)
        updated["history"] = list(updated.get("history", []))
        updated["history"].append({"role": "assistant", "content": message})
        return updated

    @staticmethod
    def apply_location(state: dict[str, Any], location: dict[str, Any]) -> dict[str, Any]:
        """Apply browser/manual location coordinates to state."""
        updated = dict(state)
        if location.get("latitude") is not None:
            updated["latitude"] = location["latitude"]
            updated["longitude"] = location["longitude"]
            updated["location_accuracy"] = location.get("accuracy", 0.0)
            updated["location_source"] = location.get("source", "browser")
        return updated

    @staticmethod
    def missing_fields(state: dict[str, Any]) -> list[str]:
        return [field for field in REQUIRED_FIELDS if state.get(field) in (None, "", [])]
