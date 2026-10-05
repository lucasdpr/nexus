from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, IdMixin


class AuditEvent(IdMixin, CreatedAtMixin, Base):
    """Registro só de inserção: a role da aplicação não tem UPDATE nem DELETE nesta tabela."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_org_created", "org_id", "created_at", "id"),)

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str | None] = mapped_column(String(32))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
