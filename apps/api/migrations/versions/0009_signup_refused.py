"""Marca as tentativas de cadastro recusadas, para não gastarem o teto global.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signup_attempts",
        sa.Column("refused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("GRANT UPDATE (refused) ON signup_attempts TO nexus_app")


def downgrade() -> None:
    op.drop_column("signup_attempts", "refused")
