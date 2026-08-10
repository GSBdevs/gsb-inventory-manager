"""Promove um perfil existente a admin (por email).

O bootstrap automático já torna o 1º usuário logado admin; use isto para promover
outra pessoa. O perfil precisa existir (criado no 1º login via Supabase).

Uso: cd backend && .venv/Scripts/python -m scripts.set_admin email@dominio.com
"""

import sys

from sqlalchemy import select

from app.core.aio import run
from app.core.database import engine, session_factory
from app.models import Base, Profile, UserRole


async def _set_admin(email: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        profile = await db.scalar(select(Profile).where(Profile.email == email))
        if profile is None:
            print(f"Nenhum perfil com email {email}. Faça login uma vez para provisioná-lo.")
            return
        profile.role = UserRole.ADMIN
        await db.commit()
        print(f"{email} agora é admin.")
    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m scripts.set_admin <email>")
        raise SystemExit(1)
    run(_set_admin(sys.argv[1]))
