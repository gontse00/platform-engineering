import logging
from fastapi import FastAPI
from sqlalchemy import text
from app.config import settings
from app.database import Base, engine
from app.routes.incidents import router as incidents_router
from app.models.incident import IncidentReport, Case, CaseTimelineEntry, CaseAssignment  # noqa

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

# Startup-safe migration: add source_session_id if missing (avoids needing Alembic for local dev)
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS source_session_id VARCHAR(100)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_cases_source_session_id ON cases(source_session_id) WHERE source_session_id IS NOT NULL"))
        conn.commit()
    logger.info("Startup migration: source_session_id column ensured")
except Exception as exc:
    logger.warning("Startup migration skipped: %s", exc)

app = FastAPI(title=settings.service_name)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except ImportError:
    pass

app.include_router(incidents_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}
