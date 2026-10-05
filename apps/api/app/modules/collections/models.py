from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, IdMixin


class Collection(IdMixin, CreatedAtMixin, Base):
    """Agrupamento de documentos (ex.: Engenharia, Jurídico) e unidade de permissão."""

    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_collections_org_id_name"),)

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))


class CollectionMember(CreatedAtMixin, Base):
    __tablename__ = "collection_members"

    # Redundante com a coleção, mas permite a mesma política de RLS das outras tabelas.
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
