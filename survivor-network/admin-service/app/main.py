"""Survivor Network Admin Service — backend-for-frontend / mission control API."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.health import router as health_router
from app.routes.dashboard import router as dashboard_router
from app.routes.cases import router as cases_router
from app.routes.participants import router as participants_router
from app.routes.assignments import router as assignments_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Survivor Network Admin Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://admin-ui.127.0.0.1.nip.io",
        "http://localhost:5174",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except ImportError:
    pass

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(cases_router)
app.include_router(participants_router)
app.include_router(assignments_router)

logger.info("admin-service started (auth_mode=%s)", settings.auth_mode)
