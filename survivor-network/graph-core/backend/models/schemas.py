from datetime import datetime
from typing import Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, BaseModel
from domain.constants import ALLOWED_EDGE_TYPES, ALLOWED_NODE_TYPES
from typing import Any

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


class TriageAssessRequest(BaseModel):
    message: str = Field(..., min_length=3)
    location: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class TriageAssessment(BaseModel):
    urgency: str
    safety_risk: str
    incident_types: list[str]
    requires_human_review: bool
    escalation_recommended: bool
    escalation_target: str | None
    rationale: list[str]


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

class EscalationDestination(BaseModel):
    kind: str
    reason: str
    node: dict[str, Any] | None = None

class TriageAssessResponse(BaseModel):
    message: str
    triage: TriageAssessment
    escalation: EscalationAssessment
    escalation_destinations: list[EscalationDestination]
    intake: dict[str, Any]

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
    recommended_actions: list[RecommendationItem]


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

class CaseIntakeRequest(BaseModel):
    message: str = Field(..., min_length=3)
    location: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    create_referrals: bool = True


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