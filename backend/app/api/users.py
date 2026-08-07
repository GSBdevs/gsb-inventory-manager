import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select

from app.core.deps import DbSession, require_roles
from app.core.pagination import paginate
from app.core.supabase import SupabaseAdmin, get_supabase_admin
from app.models import Profile, UserRole
from app.schemas.common import Page
from app.schemas.profile import ProfileOut, ProfileUpdate, UserCreate

router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[require_roles(UserRole.ADMIN)]
)

AdminClient = Annotated[SupabaseAdmin, Depends(get_supabase_admin)]


@router.get("", response_model=Page[ProfileOut])
async def list_users(db: DbSession, q: str = "", page: int = 1, size: int = 20):
    stmt = select(Profile).order_by(Profile.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Profile.email.ilike(like), Profile.full_name.ilike(like)))
    return await paginate(db, stmt, page, size)


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DbSession, admin: AdminClient):
    exists = await db.scalar(select(Profile).where(Profile.email == data.email))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um usuário com esse email")
    user_id = await admin.create_user(data.email, data.password)
    profile = Profile(
        id=uuid.UUID(user_id),
        email=data.email,
        full_name=data.full_name,
        role=data.role,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/{user_id}", response_model=ProfileOut)
async def update_user(user_id: uuid.UUID, data: ProfileUpdate, db: DbSession):
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile
