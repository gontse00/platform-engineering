"""Request/response models for agent-service."""

from pydantic import BaseModel


class SafetyFlags(BaseModel):
    immediate_danger: bool = False
    urgency_floor: str = "standard"
    matched_keywords: list[str] = []


class ConversationContext(BaseModel):
    known_location: str | None = None
    known_primary_need: str | None = None
    known_injury_status: str | None = None
    known_contact_method: str | None = None
    known_incident_summary: str | None = None
    conversation_history: list[dict] = []


class ReasonRequest(BaseModel):
    session_id: str
    message: str
    conversation_context: ConversationContext = ConversationContext()
    safety_flags: SafetyFlags = SafetyFlags()


class ExtractedFields(BaseModel):
    primary_need: str | None = None
    secondary_needs: list[str] = []
    location: str | None = None
    injury_status: str | None = None
    incident_summary: str | None = None
    safe_contact_method: str | None = None
    immediate_danger: bool | None = None


class TriageResult(BaseModel):
    suggested_urgency: str = "standard"
    safety_risk: str = "low"
    requires_escalation: bool = False
    rationale: list[str] = []


class SuggestedAction(BaseModel):
    type: str
    need: str | None = None
    location: str | None = None
    reason: str | None = None


class AgentReply(BaseModel):
    message: str


class ReasonResponse(BaseModel):
    extracted: ExtractedFields
    triage: TriageResult
    actions: list[SuggestedAction] = []
    reply: AgentReply
