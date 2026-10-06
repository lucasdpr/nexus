"""Conversas com o assistente, mensagens e citações.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = ("conversations", "messages", "citations")


def _id() -> sa.Column[object]:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def _org_fk() -> sa.Column[object]:
    return sa.Column("org_id", UUID, sa.ForeignKey("organizations.id"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "conversations",
        _id(),
        _org_fk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(120)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        _created_at(),
    )
    op.create_index(
        "ix_conversations_owner_updated", "conversations", ["org_id", "user_id", "updated_at"]
    )

    op.create_table(
        "messages",
        _id(),
        _org_fk(),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("answered", sa.Boolean),
        sa.Column("model", sa.String(64)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        _created_at(),
        sa.CheckConstraint("role IN ('USER', 'ASSISTANT')", name="ck_messages_role"),
        sa.CheckConstraint("status IN ('COMPLETE', 'FAILED')", name="ck_messages_status"),
    )
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "citations",
        _id(),
        _org_fk(),
        sa.Column(
            "message_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("marker", sa.Integer, nullable=False),
        sa.Column("chunk_id", UUID, sa.ForeignKey("chunks.id", ondelete="SET NULL")),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page", sa.Integer),
        sa.Column("quote", sa.Text, nullable=False),
        sa.Column("score", sa.Float, nullable=False),
    )
    op.create_index("ix_citations_message", "citations", ["message_id"])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (org_id = app_current_org()) WITH CHECK (org_id = app_current_org())"
        )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conversations TO nexus_app")
    op.execute("GRANT SELECT, INSERT ON messages, citations TO nexus_app")


def downgrade() -> None:
    for table in ("citations", "messages", "conversations"):
        op.drop_table(table)
