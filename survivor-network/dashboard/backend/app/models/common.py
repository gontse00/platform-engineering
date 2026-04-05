"""
Common Models - Local Survivor Network
Health check and configuration response models adapted for Kind infrastructure.
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """
    Response model for health check.
    Extended to show the status of the local Data Tier.
    """
    status: str = Field(..., example="healthy")
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    version: str = Field(default="1.0.0-local")
    
    # Infrastructure specific checks
    database: Optional[str] = Field(None, description="Status of survivor-db")
    storage: Optional[str] = Field(None, description="Status of survivor-storage")

class ConfigResponse(BaseModel):
    """
    Response model for client configuration.
    Points to your local nip.io ingress URLs.
    """
    api_base_url: str
    map_base_url: str
    version: str
    
    # Local-specific flags for the Survivor Network
    is_local_cell: bool = True
    storage_bucket: str = "survivor-assets"