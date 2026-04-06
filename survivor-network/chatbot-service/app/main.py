from fastapi import FastAPI

from app.api.routes.attachments import router as attachments_router
from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.config.settings import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.app_name)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://chatbot-ui.127.0.0.1.nip.io",
    ],
    allow_credentials=True,

    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(attachments_router)