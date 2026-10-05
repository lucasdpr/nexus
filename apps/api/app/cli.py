"""Comandos de manutenção: `python -m app.cli seed-demo`.

Rodam com a role dona do banco (sem SET ROLE), por isso não passam pelo RLS.
"""

import argparse
import asyncio
import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import create_engine
from app.core.security import hash_password, unusable_password_hash
from app.modules.collections.models import Collection, CollectionMember
from app.modules.organizations.models import Organization
from app.modules.users.models import Role, User

DEMO_SLUG = "novaforja"
DEMO_DOMAIN = "novaforja.example.com"


@dataclass(frozen=True)
class DemoPerson:
    name: str
    login: str
    role: Role
    collections: tuple[str, ...]


DEMO_COLLECTIONS = {
    "Engenharia de Manutenção": (
        "Manuais de equipamentos, planos de manutenção e relatórios técnicos."
    ),
    "Segurança do Trabalho": "Normas regulamentadoras, procedimentos e políticas de segurança.",
    "Suprimentos": "Contratos de fornecimento, especificações e políticas de compras.",
    "Jurídico e Contratos": "Contratos, aditivos e pareceres.",
}

DEMO_PEOPLE = (
    DemoPerson("Marina Duarte", "marina.duarte", Role.MANAGER, ("Engenharia de Manutenção",)),
    DemoPerson("Carlos Teixeira", "carlos.teixeira", Role.MANAGER, ("Segurança do Trabalho",)),
    DemoPerson(
        "Rafael Antunes",
        "rafael.antunes",
        Role.MEMBER,
        ("Engenharia de Manutenção", "Segurança do Trabalho"),
    ),
)


async def seed_demo(db: AsyncSession, settings: Settings) -> None:
    if await db.scalar(select(Organization).where(Organization.slug == DEMO_SLUG)):
        print("A organização de demonstração já existe; nada a fazer.")
        return

    org = Organization(name="NovaForja Industrial", slug=DEMO_SLUG, is_demo=True)
    db.add(org)
    await db.flush()

    collections = {
        name: Collection(org_id=org.id, name=name, description=description)
        for name, description in DEMO_COLLECTIONS.items()
    }
    db.add_all(collections.values())

    configured = settings.seed_admin_password
    configured_password = configured.get_secret_value() if configured else None
    admin_password = configured_password or secrets.token_urlsafe(12)
    admin = User(
        org_id=org.id,
        name="Helena Moraes",
        email=f"admin@{DEMO_DOMAIN}",
        password_hash=hash_password(admin_password),
        role=Role.ADMIN,
    )
    visitor = User(
        org_id=org.id,
        name="Visitante",
        email=settings.demo_visitor_email,
        password_hash=unusable_password_hash(),
        role=Role.MEMBER,
    )
    people = [
        (
            User(
                org_id=org.id,
                name=person.name,
                email=f"{person.login}@{DEMO_DOMAIN}",
                password_hash=unusable_password_hash(),
                role=person.role,
            ),
            person.collections,
        )
        for person in DEMO_PEOPLE
    ]
    db.add_all([admin, visitor, *(user for user, _ in people)])
    await db.flush()

    memberships = [(visitor, tuple(DEMO_COLLECTIONS)), *people]
    db.add_all(
        CollectionMember(org_id=org.id, collection_id=collections[name].id, user_id=user.id)
        for user, names in memberships
        for name in names
    )
    await db.commit()

    print(f"Organização de demonstração criada: {org.name}")
    print(f"Administrador: {admin.email}")
    if not configured_password:
        print("Senha gerada para o administrador (guarde-a, não será mostrada de novo):")
        print(admin_password)


async def _run(command: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value(), pooled=False)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            if command == "seed-demo":
                await seed_demo(db, settings)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=["seed-demo"])
    asyncio.run(_run(parser.parse_args().command))


if __name__ == "__main__":
    main()
