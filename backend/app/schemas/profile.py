import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.profile import UserRole
from app.schemas.common import UTCDateTime


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: UTCDateTime


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    role: UserRole = UserRole.OPERADOR
