import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    roles: Mapped[list] = mapped_column(MutableList.as_mutable(JSONB), default=list)
    skills: Mapped[list] = mapped_column(MutableList.as_mutable(JSONB), default=list)
    availability_status: Mapped[str] = mapped_column(String(30), default="offline")
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified")
    trust_level: Mapped[str] = mapped_column(String(20), default="low")
    home_location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    service_radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    can_transport_people: Mapped[bool] = mapped_column(Boolean, default=False)
    can_offer_shelter: Mapped[bool] = mapped_column(Boolean, default=False)
    can_offer_counselling: Mapped[bool] = mapped_column(Boolean, default=False)
    can_offer_legal_help: Mapped[bool] = mapped_column(Boolean, default=False)
    can_handle_medical: Mapped[bool] = mapped_column(Boolean, default=False)
    can_handle_crime_report: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
