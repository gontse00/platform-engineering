import logging
from fastapi import FastAPI
from app.config import settings
from app.database import Base, engine
from app.routes.incidents import router as incidents_router
from app.models.incident import IncidentReport, Case, CaseTimelineEntry, CaseAssignment  # noqa

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

Base.metadata.create_all(bind=engine)

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
