"""Documentos, etapas de processamento, trechos indexados (vetor + texto) e fila de jobs.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Fixo nesta migração: mudar a dimensão exige nova migração e reprocessamento.
EMBEDDING_DIMENSIONS = 1024
TENANT_TABLES = ("documents", "processing_steps", "chunks")


def _id() -> sa.Column[object]:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _timestamp(name: str, *, default_now: bool = False) -> sa.Column[object]:
    if default_now:
        return sa.Column(
            name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        )
    return sa.Column(name, sa.DateTime(timezone=True))


def _org_fk() -> sa.Column[object]:
    return sa.Column("org_id", UUID, sa.ForeignKey("organizations.id"), nullable=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # unaccent() não é IMMUTABLE e por isso não pode ir numa coluna gerada; com o dicionário
    # explícito o resultado é estável, e a função pode ser declarada IMMUTABLE.
    op.execute(
        """
        CREATE FUNCTION immutable_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )

    op.create_table(
        "documents",
        _id(),
        _org_fk(),
        sa.Column("collection_id", UUID, sa.ForeignKey("collections.id"), nullable=False),
        sa.Column("uploaded_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.String(500)),
        sa.Column("page_count", sa.Integer),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        _timestamp("processed_at"),
        _timestamp("deleted_at"),
        _timestamp("created_at", default_now=True),
        sa.CheckConstraint("kind IN ('PDF', 'DOCX', 'TXT', 'MD')", name="ck_documents_kind"),
        sa.CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'READY', 'FAILED')", name="ck_documents_status"
        ),
    )
    op.create_index(
        "uq_documents_org_sha256_active",
        "documents",
        ["org_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_documents_org_collection_created",
        "documents",
        ["org_id", "collection_id", "created_at"],
    )

    op.create_table(
        "processing_steps",
        _id(),
        _org_fk(),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("step", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        _timestamp("started_at"),
        _timestamp("finished_at"),
        sa.Column("error", sa.String(500)),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index(
        "uq_processing_steps_document_step",
        "processing_steps",
        ["document_id", "step"],
        unique=True,
    )

    op.create_table(
        "chunks",
        _id(),
        _org_fk(),
        sa.Column("collection_id", UUID, sa.ForeignKey("collections.id"), nullable=False),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("page", sa.Integer),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("embedding_model", sa.String(64), nullable=False),
        sa.Column(
            "tsv",
            TSVECTOR,
            sa.Computed("to_tsvector('portuguese', immutable_unaccent(content))", persisted=True),
        ),
        _timestamp("created_at", default_now=True),
    )
    op.create_index("uq_chunks_document_ordinal", "chunks", ["document_id", "ordinal"], unique=True)
    op.create_index("ix_chunks_org_collection", "chunks", ["org_id", "collection_id"])
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv)")

    op.create_table(
        "jobs",
        _id(),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False),
        _timestamp("run_after", default_now=True),
        _timestamp("locked_at"),
        _timestamp("finished_at"),
        sa.Column("last_error", sa.String(1000)),
        _timestamp("created_at", default_now=True),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'DONE', 'FAILED')", name="ck_jobs_status"
        ),
    )
    op.create_index("ix_jobs_status_run_after", "jobs", ["status", "run_after"])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (org_id = app_current_org()) WITH CHECK (org_id = app_current_org())"
        )

    op.execute("GRANT SELECT, INSERT, UPDATE ON documents TO nexus_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON processing_steps TO nexus_app")
    op.execute("GRANT SELECT, INSERT, DELETE ON chunks TO nexus_app")
    # A fila não pertence a um tenant: o worker precisa enxergá-la inteira.
    op.execute("GRANT SELECT, INSERT, UPDATE ON jobs TO nexus_app")


def downgrade() -> None:
    for table in ("jobs", "chunks", "processing_steps", "documents"):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
