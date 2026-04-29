import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class IncidentReport(Base):
    __tablename__ = "incident_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_participant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="api")  # chatbot, mobile, admin, api
    incident_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, urgent, critical
    safety_risk: Mapped[str] = mapped_column(String(20), default="low")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(30), default="new")
    needs: Mapped[list] = mapped_column(MutableList.as_mutable(JSONB), default=list)
    graph_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    incident_report_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="api")
    summary: Mapped[str] = mapped_column(Text, default="")
    incident_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")
    safety_risk: Mapped[str] = mapped_column(String(20), default="low")
    status: Mapped[str] = mapped_column(String(30), default="new")  # new, triaging, assigned, in_progress, resolved, closed, rejected
    needs: Mapped[list] = mapped_column(MutableList.as_mutable(JSONB), default=list)
    assigned_participant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graph_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class CaseTimelineEntry(Base):
    __tablename__ = "case_timeline"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(100), index=True)
    event_type: Mapped[str] = mapped_column(String(50))  # created, status_change, assignment, escalation, note
    description: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(100), index=True)
    participant_id: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50), default="responder")
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, completed, withdrawn
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
