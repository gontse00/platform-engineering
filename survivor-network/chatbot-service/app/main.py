from fastapi import FastAPI

from app.api.routes.attachments import router as attachments_router
from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.config.settings import settings

app = FastAPI(title=settings.app_name)

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(attachments_router)