from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, IdMixin


class UserSession(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "sessions"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))


class LoginAttempt(IdMixin, CreatedAtMixin, Base):
    """Tentativas de login, usadas para limitar força bruta. Não pertence a um tenant."""

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_created", "email", "created_at"),
        Index("ix_login_attempts_ip_created", "ip", "created_at"),
    )

    email: Mapped[str] = mapped_column(CITEXT)
    ip: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool]
