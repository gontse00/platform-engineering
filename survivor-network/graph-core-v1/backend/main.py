import logging
from fastapi import FastAPI
from config.settings import settings
from api.routes.graph import router as graph_router
from api.routes.search import router as search_router
from api.routes.intake import router as intake_router
from api.routes.triage import router as triage_router
from api.routes.cases import router as cases_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

app = FastAPI(title=settings.app_name)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(intake_router)
app.include_router(triage_router)
app.include_router(cases_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}