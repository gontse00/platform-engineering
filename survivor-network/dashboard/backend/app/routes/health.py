"""
Health & Configuration Routes - Local Survivor Network
Endpoints for infrastructure status and endpoint discovery within the Kind cluster.
"""
from sqlalchemy import text
from datetime import datetime, timezone
from fastapi import APIRouter

from ..config import API_BASE_URL, MAP_BASE_URL
# These now point to our local models/common.py
from ..models.common import HealthResponse, ConfigResponse
# We'll use these to ping the data tier
from ..database import engine
from ..storage import get_client

router = APIRouter(tags=["Health"])

VERSION = "1.0.0-local"

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Enhanced Health Check.
    Verifies connectivity to the Data Tier (Postgres & MinIO).
    """
    db_status = "unhealthy"
    storage_status = "unhealthy"

    # 1. Ping Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 2. Ping MinIO
    try:
        client = get_client()
        if client.bucket_exists("survivor-assets"):
            storage_status = "healthy"
    except Exception:
        storage_status = "disconnected"

    # Determine overall status
    overall = "healthy" if db_status == "healthy" and storage_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc),
        version=VERSION,
        database=db_status,
        storage=storage_status
    )

@router.get("/health", response_model=HealthResponse)
async def health():
    """Alternative health check endpoint."""
    return await health_check()

@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Get client configuration.
    Points the setup.sh script to your local nip.io Ingress URLs.
    """
    return ConfigResponse(
        api_base_url=API_BASE_URL,
        map_base_url=MAP_BASE_URL,
        version=VERSION,
        is_local_cell=True # Custom flag for local-first mode
    )