"""Marca quais tentativas de cadastro criaram conta, para o teto global contar só essas.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signup_attempts",
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("GRANT UPDATE (succeeded) ON signup_attempts TO nexus_app")


def downgrade() -> None:
    op.drop_column("signup_attempts", "succeeded")
