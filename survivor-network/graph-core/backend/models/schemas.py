"""Pydantic schemas for graph-core API.

Fixed: removed duplicate EscalationAction/EscalationAssessment classes.
Added: pre_parsed and crisis_override fields to triage/case request models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from domain.constants import ALLOWED_EDGE_TYPES, ALLOWED_NODE_TYPES
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Triage / Escalation response models
# ---------------------------------------------------------------------------

class EscalationAction(BaseModel):
    action: str
    target: str | None
    priority: str
    reason: str


class EscalationAssessment(BaseModel):
    escalate: bool
    level: str
    queue: str | None
    handoff_required: bool
    actions: list[EscalationAction]


class TriageAssessment(BaseModel):
    urgency: str
    safety_risk: str
    incident_types: list[str]
    requires_human_review: bool
    escalation_recommended: bool
    escalation_target: str | None
    rationale: list[str]


class EscalationDestination(BaseModel):
    kind: str
    reason: str
    node: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Pre-parsed data from chatbot-service (avoids redundant LLM calls)
# ---------------------------------------------------------------------------

class PreParsedIntake(BaseModel):
    """Structured intake data already extracted by chatbot-service LLM."""
    location: str | None = None
    primary_needs: list[str] = Field(default_factory=list)
    barriers: list[str] = Field(default_factory=list)
    immediate_danger: bool | None = None
    injury_status: str | None = None
    incident_summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    location_source: str | None = None  # browser, manual, text_inferred


class CrisisOverride(BaseModel):
    """Deterministic crisis safeguard data from chatbot-service."""
    min_urgency: str = "standard"
    min_safety: str = "low"
    reasons: list[str] = Field(default_factory=list)
    immediate_danger: bool = False


# ---------------------------------------------------------------------------
# Triage API request/response
# ---------------------------------------------------------------------------

class TriageAssessRequest(BaseModel):
    message: str = Field(..., min_length=3)
    location: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    pre_parsed: PreParsedIntake | None = None
    crisis_override: CrisisOverride | None = None
    latitude: float | None = None
    longitude: float | None = None


class TriageAssessResponse(BaseModel):
    message: str
    triage: TriageAssessment
    escalation: EscalationAssessment
    escalation_destinations: list[EscalationDestination]
    intake: dict[str, Any]


# ---------------------------------------------------------------------------
# Intake assessment request/response
# ---------------------------------------------------------------------------

class IntakeAssessRequest(BaseModel):
    message: str = Field(..., min_length=3, description="Free-text intake message from user")
    location: str | None = Field(default=None, description="Optional explicit location override")
    top_k: int = Field(default=5, ge=1, le=20)


class RecommendationItem(BaseModel):
    kind: str
    category: str
    reason: str
    node: dict[str, Any] | None = None


class IntakeAssessResponse(BaseModel):
    message: str
    summary: str
    normalized_location: str | None
    primary_needs: list[str]
    derived_support_needs: list[str]
    normalized_barriers: list[str]
    matched_need_nodes: list[dict[str, Any]]
    matched_resources: list[dict[str, Any]]
    matched_helpers: list[dict[str, Any]]
    semantic_results: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    ranked_destinations: list[dict[str, Any]] = Field(default_factory=list)
    routing_summary: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Graph node/edge CRUD
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    node_type: str
    label: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("node_type", "label")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, value: str) -> str:
        if value not in ALLOWED_NODE_TYPES:
            raise ValueError(f"node_type must be one of: {sorted(ALLOWED_NODE_TYPES)}")
        return value


class NodeResponse(BaseModel):
    id: UUID
    node_type: str
    label: str
    metadata: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class EdgeCreate(BaseModel):
    from_node_id: UUID
    to_node_id: UUID
    edge_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("edge_type")
    @classmethod
    def edge_type_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("edge_type")
    @classmethod
    def validate_edge_type(cls, value: str) -> str:
        if value not in ALLOWED_EDGE_TYPES:
            raise ValueError(f"edge_type must be one of: {sorted(ALLOWED_EDGE_TYPES)}")
        return value


class EdgeResponse(BaseModel):
    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    edge_type: str
    metadata: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class NeighborResponse(BaseModel):
    edge_id: UUID
    edge_type: str
    direction: str
    node: NodeResponse
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Case models
# ---------------------------------------------------------------------------

class CaseGraphResponse(BaseModel):
    case: NodeResponse
    neighbors: list[NeighborResponse]


class MatchResultNode(BaseModel):
    id: UUID
    node_type: str
    label: str
    metadata: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchmakingResult(BaseModel):
    need: NodeResponse
    matches: list[MatchResultNode]


class SupportOptionsResponse(BaseModel):
    survivor: NodeResponse
    needs: list[NodeResponse]
    resources: list[NodeResponse]
    helpers: list[NodeResponse]

class SurvivorSupportView(BaseModel):
    survivor: NodeResponse
    needs: list[NodeResponse]
    resources: list[NodeResponse]
    helpers: list[NodeResponse]


class CaseSupportOptionsResponse(BaseModel):
    case: NodeResponse
    survivors: list[SurvivorSupportView]

class LocationSupportOptionsResponse(BaseModel):
    location: NodeResponse
    survivors: list[NodeResponse]
    cases: list[NodeResponse]
    needs: list[NodeResponse]
    resources: list[NodeResponse]
    helpers: list[NodeResponse]

class NodeUpdate(BaseModel):
    label: str | None = None
    metadata: Dict[str, Any] | None = None

class EdgeUpdate(BaseModel):
    metadata: Dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Search models
# ---------------------------------------------------------------------------

class SearchDocumentResponse(BaseModel):
    id: UUID
    doc_type: str
    source_node_id: UUID
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResultsResponse(BaseModel):
    query: str
    filters: Dict[str, Any]
    total: int
    limit: int
    offset: int
    results: list[SearchDocumentResponse]

class SemanticSearchDocumentResponse(BaseModel):
    id: UUID
    doc_type: str
    source_node_id: UUID
    title: str
    content: str
    snippet: str
    metadata: Dict[str, Any]
    score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticSearchResultsResponse(BaseModel):
    query: str
    total: int
    limit: int
    results: list[SemanticSearchDocumentResponse]


# ---------------------------------------------------------------------------
# Case intake / context update
# ---------------------------------------------------------------------------

class CaseIntakeRequest(BaseModel):
    message: str = Field(..., min_length=3)
    location: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    create_referrals: bool = True
    pre_parsed: PreParsedIntake | None = None
    crisis_override: CrisisOverride | None = None
    latitude: float | None = None
    longitude: float | None = None


class PersistedCaseNodes(BaseModel):
    survivor: dict[str, Any]
    case: dict[str, Any]
    assessment: dict[str, Any] | None = None
    referrals: list[dict[str, Any]] = Field(default_factory=list)


class CaseIntakeResponse(BaseModel):
    message: str
    summary: str
    intake: dict[str, Any]
    triage: TriageAssessment
    escalation: EscalationAssessment
    escalation_destinations: list[EscalationDestination]
    persisted: PersistedCaseNodes

class CaseContextUpdateRequest(BaseModel):
    session_id: str | None = None
    immediate_danger: bool | None = None
    injury_status: str | None = None
    safe_contact_method: str | None = None
    location: str | None = None
    primary_need: str | None = None
    conversation_summary: str | None = None
    submission_mode: str | None = None


class CaseContextUpdateResponse(BaseModel):
    case_id: str
    updated: bool
    message: str

class CaseTimelineEvent(BaseModel):
    node_id: str
    node_type: str
    label: str
    edge_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

class CaseTimelineResponse(BaseModel):
    case_id: str
    events: list[CaseTimelineEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Routing / scoring models
# ---------------------------------------------------------------------------

class RouteScoreBreakdown(BaseModel):
    need_match: float = 0.0
    location_match: float = 0.0
    urgency_fit: float = 0.0
    barrier_support: float = 0.0
    availability: float = 0.0


class RankedDestination(BaseModel):
    node_id: str
    node_type: str
    label: str
    score: float
    score_breakdown: RouteScoreBreakdown
    why_selected: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingSummary(BaseModel):
    top_destination_label: Optional[str] = None
    top_destination_type: Optional[str] = None
    total_ranked: int = 0
    notes: List[str] = Field(default_factory=list)
