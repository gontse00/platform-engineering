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
            "attachments": [],
            "history": [],
            "latest_graph_assessment": None,
            "submission_mode": None,
        }

    @staticmethod
    def apply_user_message(state: dict[str, Any], message: str) -> dict[str, Any]:
        updated = dict(state)
        updated["history"] = list(updated.get("history", []))
        updated["history"].append({"role": "user", "content": message})

        text = message.lower()

        if updated.get("incident_summary") is None and len(message.strip()) > 8:
            updated["incident_summary"] = message.strip()

        if updated.get("location") is None:
            if "johannesburg" in text or "joburg" in text or "jhb" in text:
                updated["location"] = "Johannesburg"

        if updated.get("immediate_danger") is None:
            if (
                "immediate danger" in text
                or "not safe" in text
                or "danger" in text
                or "unsafe" in text
            ):
                updated["immediate_danger"] = True
            elif "safe now" in text or "not in danger" in text:
                updated["immediate_danger"] = False

        if updated.get("injury_status") is None:
            if "bleeding" in text or "injured" in text or "hurt" in text:
                updated["injury_status"] = "injured"
            elif "not injured" in text:
                updated["injury_status"] = "not_injured"

        if updated.get("primary_need") is None:
            if "medical" in text or "clinic" in text or "bleeding" in text:
                updated["primary_need"] = "Emergency Medical"
            elif "shelter" in text or "safe place" in text:
                updated["primary_need"] = "Emergency Shelter"
            elif "legal" in text or "protection order" in text:
                updated["primary_need"] = "Protection Order Support"
            elif "talk to someone" in text or "traumatized" in text or "counselling" in text:
                updated["primary_need"] = "Mental Health Support"

        if updated.get("safe_contact_method") is None:
            if (
                "text me" in text
                or "message me" in text
                or "text is safer" in text
                or "text is safe" in text
                or "sms is safer" in text
                or "message is safer" in text
            ):
                updated["safe_contact_method"] = "text"
            elif (
                "call me" in text
                or "phone call" in text
                or "calling is okay" in text
                or "you can call" in text
            ):
                updated["safe_contact_method"] = "call"

        return updated

    @staticmethod
    def missing_fields(state: dict[str, Any]) -> list[str]:
        return [field for field in REQUIRED_FIELDS if state.get(field) in (None, "", [])]