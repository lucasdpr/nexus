"""Arquivos enviados guardados no próprio Postgres (armazenamento durável sem serviço extra).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("data", BYTEA, nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    # Só o armazenamento (role dona do banco) lê e grava aqui. As chaves são `<org>/<documento>`
    # geradas pela aplicação, e a role `nexus_app`, que passa pelo RLS, nunca recebe acesso.
    op.execute("REVOKE ALL ON stored_files FROM nexus_app")


def downgrade() -> None:
    op.drop_table("stored_files")
