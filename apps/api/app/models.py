"""Importa todos os modelos para registrá-los no metadata (usado pelo Alembic)."""

from app.core.models import Base
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.collections.models import Collection, CollectionMember
from app.modules.organizations.models import Organization
from app.modules.users.models import User

__all__ = [
    "AuditEvent",
    "Base",
    "Collection",
    "CollectionMember",
    "LoginAttempt",
    "Organization",
    "User",
    "UserSession",
]
