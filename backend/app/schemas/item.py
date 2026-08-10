import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class ItemCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    sku: str = ""
    category_id: uuid.UUID | None = None
    unidade: str = "un"
    estoque_minimo: int = Field(default=0, ge=0)
    observacoes: str = ""


class ItemUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = None
    category_id: uuid.UUID | None = None
    unidade: str | None = None
    estoque_minimo: int | None = Field(default=None, ge=0)
    observacoes: str | None = None
    ativo: bool | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    nome: str
    category_id: uuid.UUID | None
    unidade: str
    estoque_minimo: int
    saldo: int = Field(validation_alias="saldo_cache")
    ativo: bool
    observacoes: str
    created_at: UTCDateTime


class AdjustIn(BaseModel):
    novo_saldo: int = Field(ge=0)
    motivo: str = ""
