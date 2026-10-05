"""Núcleo: organizações, usuários, sessões, coleções, auditoria e isolamento por RLS.

Revision ID: 0001
Revises:
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = ("users", "sessions", "collections", "collection_members", "audit_events")


def _id() -> sa.Column[object]:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def _org_fk() -> sa.Column[object]:
    return sa.Column("org_id", UUID, sa.ForeignKey("organizations.id"), nullable=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "organizations",
        _id(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.false()),
        _created_at(),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    op.create_table(
        "users",
        _id(),
        _org_fk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", CITEXT, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        _created_at(),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('ADMIN', 'MANAGER', 'MEMBER')", name="ck_users_role"),
        sa.CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_users_status"),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])

    op.create_table(
        "sessions",
        _id(),
        _org_fk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(500)),
        _created_at(),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_org_id", "sessions", ["org_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "login_attempts",
        _id(),
        sa.Column("email", CITEXT, nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("success", sa.Boolean, nullable=False),
        _created_at(),
    )
    op.create_index("ix_login_attempts_email_created", "login_attempts", ["email", "created_at"])
    op.create_index("ix_login_attempts_ip_created", "login_attempts", ["ip", "created_at"])

    op.create_table(
        "collections",
        _id(),
        _org_fk(),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500)),
        _created_at(),
        sa.UniqueConstraint("org_id", "name", name="uq_collections_org_id_name"),
    )
    op.create_index("ix_collections_org_id", "collections", ["org_id"])

    op.create_table(
        "collection_members",
        _org_fk(),
        sa.Column(
            "collection_id",
            UUID,
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        _created_at(),
    )
    op.create_index("ix_collection_members_org_id", "collection_members", ["org_id"])
    op.create_index("ix_collection_members_user_id", "collection_members", ["user_id"])

    op.create_table(
        "audit_events",
        _id(),
        _org_fk(),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(32)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("ip", sa.String(64)),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        _created_at(),
    )
    op.create_index("ix_audit_events_org_created", "audit_events", ["org_id", "created_at", "id"])

    _create_app_role_and_grants()
    _enable_row_level_security()
    _create_auth_functions()


def _create_app_role_and_grants() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nexus_app') THEN
            CREATE ROLE nexus_app NOLOGIN NOBYPASSRLS;
          END IF;
        END $$
        """
    )
    # A role de login assume nexus_app a cada transação (SET LOCAL ROLE), sem herdar privilégios.
    op.execute("GRANT nexus_app TO CURRENT_USER WITH INHERIT FALSE, SET TRUE")
    op.execute("GRANT USAGE ON SCHEMA public TO nexus_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON organizations, users, sessions TO nexus_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON collections TO nexus_app")
    op.execute("GRANT SELECT, INSERT, DELETE ON collection_members TO nexus_app")
    # Auditoria e tentativas de login: só leitura e inserção.
    op.execute("GRANT SELECT, INSERT ON audit_events, login_attempts TO nexus_app")


def _enable_row_level_security() -> None:
    op.execute(
        """
        CREATE FUNCTION app_current_org() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$ SELECT nullif(current_setting('app.org_id', true), '')::uuid $$
        """
    )
    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON organizations "
        "USING (id = app_current_org()) WITH CHECK (id = app_current_org())"
    )
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (org_id = app_current_org()) WITH CHECK (org_id = app_current_org())"
        )


def _create_auth_functions() -> None:
    """Únicos caminhos que leem dados sem organização definida: localizar a conta no login,
    resolver o cookie de sessão e entrar na demonstração. Rodam como dono (SECURITY DEFINER)
    e devolvem só as colunas necessárias."""
    op.execute(
        """
        CREATE FUNCTION auth_find_user(p_email citext)
        RETURNS TABLE (user_id uuid, org_id uuid, password_hash varchar, status varchar)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
          SELECT u.id, u.org_id, u.password_hash, u.status FROM users u WHERE u.email = p_email
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION auth_resolve_session(p_token_hash bytea)
        RETURNS TABLE (session_id uuid, user_id uuid, org_id uuid, role varchar)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
          SELECT s.id, u.id, u.org_id, u.role
          FROM sessions s JOIN users u ON u.id = s.user_id
          WHERE s.token_hash = p_token_hash
            AND s.revoked_at IS NULL
            AND s.expires_at > now()
            AND u.status = 'ACTIVE'
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION auth_demo_visitor(p_email citext)
        RETURNS TABLE (user_id uuid, org_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
          SELECT u.id, u.org_id
          FROM users u JOIN organizations o ON o.id = u.org_id
          WHERE u.email = p_email AND o.is_demo AND u.status = 'ACTIVE'
        $$
        """
    )
    for signature in (
        "auth_find_user(citext)",
        "auth_resolve_session(bytea)",
        "auth_demo_visitor(citext)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO nexus_app")


def downgrade() -> None:
    for function in (
        "auth_demo_visitor(citext)",
        "auth_resolve_session(bytea)",
        "auth_find_user(citext)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
    for table in (
        "audit_events",
        "collection_members",
        "collections",
        "login_attempts",
        "sessions",
        "users",
        "organizations",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS app_current_org()")
