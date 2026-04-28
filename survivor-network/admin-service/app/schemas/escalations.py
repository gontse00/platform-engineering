from pydantic import BaseModel


class EscalationResponse(BaseModel):
    escalated: bool
    case_id: str
    target: str
    notification_sent: bool = False
    warnings: list[str] = []
