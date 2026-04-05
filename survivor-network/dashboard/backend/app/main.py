"""
Way Back Home - Mission Control API (Local Survivor Edition)
Backend service for the local Kind cluster infrastructure.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

from .config import get_cors_origins, get_cors_origin_regex
# We will create these local route files next
from .routes import health, events, participants, admin, auth 
from .database import create_tables

# =============================================================================
# Lifecycle Management (Infrastructure Readiness)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Infrastructure Readiness: Create tables and verify connectivity.
    """
    print("🚀 Checking Survivor Infrastructure readiness...")
    
    # Trigger the SQLAlchemy table creation here
    try:
        await create_tables()
        print("✅ Database tables verified/created.")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        # In a real production app at FNB, you might want to 
        # raise an error here to prevent the pod from starting 'degraded'
    
    yield
    print("🛑 Shutting down Mission Control...")

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Survivor Network - Mission Control",
    description="Local Open-Source Backend for Disaster Response Coordination",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# CORS Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=get_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Include Routers
# =============================================================================
from .dependencies import verify_admin

async def skip_verify_admin():
    return "local-dev-admin@northcliff.node"

# 3. Apply the override to the FastAPI app instance
app.dependency_overrides[verify_admin] = skip_verify_admin
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(participants.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
