from pydantic import BaseModel
from datetime import datetime

class IncidentReportCreate(BaseModel):
    reporter_participant_id: str | None = None
    source: str = "api"
    incident_type: str | None = None
    summary: str
    description: str | None = None
    location_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    urgency: str = "medium"
    safety_risk: str = "low"
    needs: list[str] = []

class IncidentReportResponse(BaseModel):
    id: str
    reporter_participant_id: str | None
    source: str
    incident_type: str | None
    summary: str
    description: str | None
    location_text: str | None
    latitude: float | None
    longitude: float | None
    urgency: str
    safety_risk: str
    status: str
    needs: list
    created_at: datetime
    model_config = {"from_attributes": True}

class CaseCreate(BaseModel):
    incident_report_id: str | None = None
    source: str = "api"
    summary: str
    incident_type: str | None = None
    location_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    urgency: str = "medium"
    safety_risk: str = "low"
    needs: list[str] = []


class CaseFromIntake(BaseModel):
    session_id: str | None = None
    message: str
    location_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    urgency: str = "medium"
    safety_risk: str = "low"
    primary_need: str | None = None
    secondary_needs: list[str] = []
    injury_status: str | None = None
    immediate_danger: bool = False
    incident_type: str | None = None

class CaseResponse(BaseModel):
    id: str
    source_session_id: str | None = None
    incident_report_id: str | None
    source: str
    summary: str
    incident_type: str | None
    location_text: str | None
    latitude: float | None
    longitude: float | None
    urgency: str
    safety_risk: str
    status: str
    needs: list
    assigned_participant_id: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class StatusUpdate(BaseModel):
    status: str
    reason: str | None = None

class TimelineEntryCreate(BaseModel):
    event_type: str
    description: str
    actor: str | None = None

class TimelineEntryResponse(BaseModel):
    id: str
    case_id: str
    event_type: str
    description: str
    actor: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

class AssignmentCreate(BaseModel):
    participant_id: str
    role: str = "responder"
