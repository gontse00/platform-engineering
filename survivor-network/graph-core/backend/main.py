from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api.routes.graph import router as graph_router
from api.routes.search import router as search_router
from api.routes.intake import router as intake_router
from api.routes.triage import router as triage_router
from api.routes.cases import router as cases_router
from api.routes.admin import router as admin_router
from logging_config import RequestIdMiddleware, setup_logging

setup_logging(service_name=settings.app_name)

app = FastAPI(title=settings.app_name)

app.add_middleware(RequestIdMiddleware)
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

app.include_router(graph_router)
app.include_router(search_router)
app.include_router(intake_router)
app.include_router(triage_router)
app.include_router(cases_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}
