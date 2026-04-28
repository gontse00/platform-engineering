from pydantic import BaseModel
from datetime import datetime

class ParticipantCreate(BaseModel):
    display_name: str
    phone: str | None = None
    email: str | None = None
    roles: list[str] = []
    skills: list[str] = []
    availability_status: str = "offline"
    verification_status: str = "unverified"
    trust_level: str = "low"
    home_location_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    service_radius_km: float | None = None
    can_transport_people: bool = False
    can_offer_shelter: bool = False
    can_offer_counselling: bool = False
    can_offer_legal_help: bool = False
    can_handle_medical: bool = False
    can_handle_crime_report: bool = False

class ParticipantResponse(BaseModel):
    id: str
    display_name: str
    phone: str | None
    email: str | None
    roles: list
    skills: list
    availability_status: str
    verification_status: str
    trust_level: str
    home_location_text: str | None
    latitude: float | None
    longitude: float | None
    service_radius_km: float | None
    can_transport_people: bool
    can_offer_shelter: bool
    can_offer_counselling: bool
    can_offer_legal_help: bool
    can_handle_medical: bool
    can_handle_crime_report: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class AvailabilityUpdate(BaseModel):
    availability_status: str

class VerificationUpdate(BaseModel):
    verification_status: str

class SearchAvailable(BaseModel):
    urgency: str = "medium"
    safety_risk: str = "low"
    needs: list[str] = []
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float = 20.0
