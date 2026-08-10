import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class CategoryCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    parent_id: uuid.UUID | None = None
    descricao: str = ""


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    parent_id: uuid.UUID | None
    descricao: str
    created_at: UTCDateTime
