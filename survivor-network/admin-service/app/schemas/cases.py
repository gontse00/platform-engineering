from pydantic import BaseModel


class StatusUpdateRequest(BaseModel):
    status: str
    note: str | None = None


class EscalateRequest(BaseModel):
    target: str  # priority_support_queue, police, medical, gbv_support, legal_support, admin_review
    reason: str
    notify: bool = True


class CaseDetailResponse(BaseModel):
    case: dict | None = None
    graph_context: dict | None = None
    attachments: list = []
    assignments: list = []
    warnings: list[str] = []
