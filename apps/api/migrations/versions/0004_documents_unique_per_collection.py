"""Duplicata de documento passa a valer por coleção, não pela organização inteira.

Com a regra por organização, quem enviava um arquivo descobria que ele já existia numa
coleção que não podia ver.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.drop_index("uq_documents_org_sha256_active", table_name="documents")
    op.create_index(
        "uq_documents_collection_sha256_active",
        "documents",
        ["org_id", "collection_id", "sha256"],
        unique=True,
        postgresql_where=ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("uq_documents_collection_sha256_active", table_name="documents")
    op.create_index(
        "uq_documents_org_sha256_active",
        "documents",
        ["org_id", "sha256"],
        unique=True,
        postgresql_where=ACTIVE,
    )
