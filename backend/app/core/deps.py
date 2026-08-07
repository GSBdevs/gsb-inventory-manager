import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_supabase_jwt
from app.models import Profile, UserRole

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _provision_profile(db: AsyncSession, user_id: uuid.UUID, email: str) -> Profile:
    """Carrega o perfil do usuário; cria no primeiro acesso. Se ainda não há nenhum
    admin, o primeiro perfil provisionado vira admin (bootstrap)."""
    profile = await db.get(Profile, user_id)
    if profile is not None:
        return profile
    admin_count = await db.scalar(
        select(func.count()).select_from(Profile).where(Profile.role == UserRole.ADMIN)
    )
    role = UserRole.ADMIN if not admin_count else UserRole.OPERADOR
    profile = Profile(id=user_id, email=email or "", role=role)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> Profile:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou ausentes",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_supabase_jwt(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None

    profile = await _provision_profile(db, user_id, claims.get("email", ""))
    if not profile.is_active:
        raise unauthorized
    return profile


CurrentUser = Annotated[Profile, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def _check(user: CurrentUser) -> Profile:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação",
            )
        return user

    return Depends(_check)
