from typing import Any
from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    initial_message: str | None = None


class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    stage: str
    bot_message: str
    next_expected_fields: list[str] = Field(default_factory=list)


class SessionMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    client_message_id: str | None = None


class SessionAttachmentResponse(BaseModel):
    attachment_id: str
    attachment_type: str
    filename: str | None = None


class SessionStateResponse(BaseModel):
    session_id: str
    status: str
    stage: str
    escalated: bool
    provisional_case_id: str | None = None
    latest_urgency: str | None = None
    latest_queue: str | None = None
    state: dict[str, Any]
    message_count: int
    attachment_count: int


class SessionTurnResponse(BaseModel):
    session_id: str
    status: str
    stage: str
    bot_message: str
    needs_more_info: bool
    missing_fields: list[str] = Field(default_factory=list)
    escalation: dict[str, Any] | None = None
    provisional_case: dict[str, Any] | None = None
    latest_assessment: dict[str, Any] | None = None


class SubmitSessionResponse(BaseModel):
    session_id: str
    status: str
    stage: str
    provisional_case_id: str | None = None
    submitted: bool
    missing_fields: list[str] = Field(default_factory=list)
    state: dict[str, Any]
    message: str | None = None