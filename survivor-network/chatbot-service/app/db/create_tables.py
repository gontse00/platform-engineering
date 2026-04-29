"""Simple table creation script — no Alembic dependency.

Used by Helm initContainer to bootstrap tables on a fresh database.
Safe to run multiple times (CREATE TABLE IF NOT EXISTS via create_all).
"""

import sys
import os

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.base import Base
from app.db.session import engine
from app.models.session import ChatAttachmentDB, ChatMessageDB, ChatSessionDB  # noqa: F401

if __name__ == "__main__":
    print("Creating chatbot-service tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created (if not already present).")
