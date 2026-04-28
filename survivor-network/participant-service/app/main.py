import logging
from fastapi import FastAPI
from app.config import settings
from app.database import Base, engine
from app.routes.participants import router as participants_router
from app.models.participant import Participant  # noqa

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.service_name)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except ImportError:
    pass

app.include_router(participants_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}
