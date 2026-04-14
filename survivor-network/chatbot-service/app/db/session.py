from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)