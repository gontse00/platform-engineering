"""Bring chatbot schema to the current application baseline.

Revision ID: 20260405_0001
Revises:
Create Date: 2026-04-05 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260405_0001"
down_revision = None
branch_labels = None
depends_on = None


CHAT_SESSIONS = "chat_sessions"
CHAT_MESSAGES = "chat_messages"
CHAT_ATTACHMENTS = "chat_attachments"
ALEMBIC_VERSION = "alembic_version"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists(CHAT_SESSIONS):
        op.create_table(
            CHAT_SESSIONS,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
            sa.Column("stage", sa.String(length=100), nullable=False, server_default="initial"),
            sa.Column("provisional_case_id", sa.String(length=100), nullable=True),
            sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("latest_urgency", sa.String(length=50), nullable=True),
            sa.Column("latest_queue", sa.String(length=100), nullable=True),
            sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_user_message_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    session_columns = _column_names(CHAT_SESSIONS)
    if "submitted_at" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    if "closed_at" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    if "last_user_message_at" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("last_user_message_at", sa.DateTime(timezone=True), nullable=True))
    if "last_assessed_at" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True))
    if "latest_urgency" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("latest_urgency", sa.String(length=50), nullable=True))
    if "latest_queue" not in session_columns:
        op.add_column(CHAT_SESSIONS, sa.Column("latest_queue", sa.String(length=100), nullable=True))
    if "state_json" not in session_columns:
        op.add_column(
            CHAT_SESSIONS,
            sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )

    if not _table_exists(CHAT_MESSAGES):
        op.create_table(
            CHAT_MESSAGES,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("client_message_id", sa.String(length=100), nullable=True),
            sa.Column("extracted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    message_columns = _column_names(CHAT_MESSAGES)
    if "client_message_id" not in message_columns:
        op.add_column(CHAT_MESSAGES, sa.Column("client_message_id", sa.String(length=100), nullable=True))
    if "extracted_json" not in message_columns:
        op.add_column(
            CHAT_MESSAGES,
            sa.Column("extracted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )

    message_indexes = _index_names(CHAT_MESSAGES)
    if "ix_chat_messages_session_id" not in message_indexes:
        op.create_index("ix_chat_messages_session_id", CHAT_MESSAGES, ["session_id"], unique=False)
    if "ix_chat_messages_client_message_id" not in message_indexes:
        op.create_index("ix_chat_messages_client_message_id", CHAT_MESSAGES, ["client_message_id"], unique=False)

    if not _table_exists(CHAT_ATTACHMENTS):
        op.create_table(
            CHAT_ATTACHMENTS,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
            sa.Column("attachment_type", sa.String(length=50), nullable=False),
            sa.Column("storage_path", sa.Text(), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    attachment_columns = _column_names(CHAT_ATTACHMENTS)
    if "original_filename" not in attachment_columns:
        op.add_column(CHAT_ATTACHMENTS, sa.Column("original_filename", sa.String(length=255), nullable=True))
    if "metadata_json" not in attachment_columns:
        op.add_column(
            CHAT_ATTACHMENTS,
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )

    attachment_indexes = _index_names(CHAT_ATTACHMENTS)
    if "ix_chat_attachments_session_id" not in attachment_indexes:
        op.create_index("ix_chat_attachments_session_id", CHAT_ATTACHMENTS, ["session_id"], unique=False)


def downgrade() -> None:
    if _table_exists(CHAT_ATTACHMENTS):
        attachment_indexes = _index_names(CHAT_ATTACHMENTS)
        if "ix_chat_attachments_session_id" in attachment_indexes:
            op.drop_index("ix_chat_attachments_session_id", table_name=CHAT_ATTACHMENTS)
        op.drop_table(CHAT_ATTACHMENTS)

    if _table_exists(CHAT_MESSAGES):
        message_indexes = _index_names(CHAT_MESSAGES)
        if "ix_chat_messages_client_message_id" in message_indexes:
            op.drop_index("ix_chat_messages_client_message_id", table_name=CHAT_MESSAGES)
        if "ix_chat_messages_session_id" in message_indexes:
            op.drop_index("ix_chat_messages_session_id", table_name=CHAT_MESSAGES)
        op.drop_table(CHAT_MESSAGES)

    if _table_exists(CHAT_SESSIONS):
        op.drop_table(CHAT_SESSIONS)
