import uuid

from pydantic import BaseModel, ConfigDict, Field


class TechnicianCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)


class TechnicianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    ativo: bool
