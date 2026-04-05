"""
Event Models - Local Survivor Network
Request and response models for mission coordination.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EventCreate(BaseModel):
    """Request model for creating a new mission (event)."""
    code: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    # Defaults to your local config if not provided
    max_participants: Optional[int] = Field(default=500, ge=10, le=10000)

class EventResponse(BaseModel):
    """Response model for mission information."""
    # SQLAlchemy compatibility
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: Optional[str] = None
    max_participants: int
    participant_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None  # Local admin email
    active: bool = True