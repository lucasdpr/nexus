from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.audit import service
from app.modules.audit.schemas import AuditEventOut, AuditEventPage
from app.modules.auth.dependencies import DbSession, require_roles
from app.modules.auth.identity import CurrentUser
from app.modules.users.models import Role

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("")
async def list_audit_events(
    db: DbSession,
    current: Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    action: str | None = None,
) -> AuditEventPage:
    rows, next_cursor = await service.list_events(
        db, current.org_id, limit=limit, cursor=cursor, action=action
    )
    items = [
        AuditEventOut(
            id=event.id,
            action=event.action,
            actor_id=event.actor_id,
            actor_name=actor_name,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            ip=event.ip,
            details=event.details,
            created_at=event.created_at,
        )
        for event, actor_name in rows
    ]
    return AuditEventPage(items=items, next_cursor=next_cursor)
