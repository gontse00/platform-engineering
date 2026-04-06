from pathlib import Path

from alembic import command
from alembic.config import Config

from app.db.base import Base
from app.db.session import engine
from app.models.session import ChatAttachmentDB, ChatMessageDB, ChatSessionDB  # noqa: F401


def _alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    return config


def init_db() -> None:
    # Bootstrap any brand-new database objects first so a fresh environment can start cleanly.
    Base.metadata.create_all(bind=engine)

    # Then run migrations to bring older environments forward safely.
    command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
