from pydantic import BaseModel


class AssignRequest(BaseModel):
    participant_id: str
    assignment_type: str = "helper"  # helper, responder, driver, counsellor, legal_advisor, medical_support, admin_owner
    note: str | None = None
    notify_participant: bool = True


class RecommendRequest(BaseModel):
    needs: list[str] = []
    location_text: str | None = None
    urgency: str = "medium"
    safety_risk: str = "low"
    limit: int = 10


class AssignResponse(BaseModel):
    assigned: bool
    case_id: str
    participant_id: str
    assignment: dict | None = None
    warnings: list[str] = []
