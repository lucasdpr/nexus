"""Cadastros por IP, para limitar a criação de contas em massa.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signup_attempts",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_signup_attempts_ip_created", "signup_attempts", ["ip", "created_at"])
    # Como login_attempts, não pertence a uma organização (o cadastro cria a organização).
    op.execute("GRANT SELECT, INSERT ON signup_attempts TO nexus_app")


def downgrade() -> None:
    op.drop_table("signup_attempts")
