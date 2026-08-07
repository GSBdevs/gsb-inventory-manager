import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERADOR = "operador"


class Profile(TableBase):
    """Papel e metadados do usuário. A identidade (senha/login) vive no Supabase Auth;
    `id` é o `auth.users.id` do Supabase — por isso, sem gerador default."""

    __tablename__ = "profiles"

    # Sobrescreve o id do TableBase para NÃO gerar UUID: recebemos o id do Supabase.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True, default="")
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.OPERADOR
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
