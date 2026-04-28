from pydantic import BaseModel


class VerificationUpdateRequest(BaseModel):
    verification_status: str
    reason: str | None = None


class AvailabilityUpdateRequest(BaseModel):
    availability_status: str
