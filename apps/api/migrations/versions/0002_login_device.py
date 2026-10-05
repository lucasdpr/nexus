"""Dispositivo da tentativa de login, para reconhecer navegadores já usados com sucesso.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("login_attempts", sa.Column("device_hash", sa.LargeBinary(32)))
    op.create_index(
        "ix_login_attempts_email_device",
        "login_attempts",
        ["email", "device_hash"],
        postgresql_where=sa.text("success AND device_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempts_email_device", table_name="login_attempts")
    op.drop_column("login_attempts", "device_hash")
