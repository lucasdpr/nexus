from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    # UUIDv7: ordenado no tempo, bom para índices B-tree.
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def str_enum(enum: type[StrEnum]) -> Enum:
    """Enum guardado como texto (sem tipo ENUM do Postgres, que complica migrações)."""
    return Enum(enum, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e])
