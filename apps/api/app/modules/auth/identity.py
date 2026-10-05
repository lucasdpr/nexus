from dataclasses import dataclass
from uuid import UUID

from app.modules.users.models import Role


@dataclass(frozen=True, slots=True)
class CurrentUser:
    user_id: UUID
    org_id: UUID
    role: Role
    session_id: UUID


@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip: str | None
    user_agent: str | None
