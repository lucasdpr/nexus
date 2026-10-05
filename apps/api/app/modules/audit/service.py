import base64
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.models import AuditEvent
from app.modules.users.models import User


def record(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_id: UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | str | None = None,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Adiciona o evento à transação corrente; é gravado junto com a ação auditada."""
    db.add(
        AuditEvent(
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip=ip,
            details=details or {},
        )
    )


def encode_cursor(created_at: datetime, event_id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{event_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        created_at, event_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created_at), UUID(event_id)
    except ValueError as exc:
        raise DomainError("Cursor de paginação inválido.") from exc


async def list_events(
    db: AsyncSession,
    org_id: UUID,
    *,
    limit: int,
    cursor: str | None,
    action: str | None,
) -> tuple[Sequence[Row[AuditEvent, str]], str | None]:
    """Paginação por cursor (keyset): estável e eficiente mesmo com muitos eventos."""
    query = (
        select(AuditEvent, User.name)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .where(AuditEvent.org_id == org_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit + 1)
    )
    if action:
        query = query.where(AuditEvent.action == action)
    if cursor:
        query = query.where(tuple_(AuditEvent.created_at, AuditEvent.id) < decode_cursor(cursor))

    rows = (await db.execute(query)).all()
    if len(rows) <= limit:
        return rows, None
    rows = rows[:limit]
    last = rows[-1][0]
    return rows, encode_cursor(last.created_at, last.id)
