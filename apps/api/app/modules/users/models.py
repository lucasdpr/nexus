from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, IdMixin


class Role(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


def _str_enum(enum: type[StrEnum]) -> Enum:
    return Enum(enum, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e])


class User(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    # Único em todo o sistema: o login não pergunta a organização.
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[Role] = mapped_column(_str_enum(Role))
    status: Mapped[UserStatus] = mapped_column(_str_enum(UserStatus), default=UserStatus.ACTIVE)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
