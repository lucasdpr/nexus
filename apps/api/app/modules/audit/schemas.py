from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: UUID
    action: str
    actor_id: UUID | None
    actor_name: str | None
    resource_type: str | None
    resource_id: str | None
    ip: str | None
    details: dict[str, Any]
    created_at: datetime


class AuditEventPage(BaseModel):
    items: list[AuditEventOut]
    next_cursor: str | None
