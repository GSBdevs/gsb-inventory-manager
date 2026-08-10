import uuid

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.movement import MovementType
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

    @computed_field
    @property
    def status(self) -> str:
        saldo, minimo = self.saldo, self.estoque_minimo
        if saldo <= 0:
            return "Em falta"
        if minimo > 0 and saldo < minimo:
            return "Ruim"
        if minimo > 0 and saldo < minimo * 2:
            return "Alerta"
        return "Bom"


class AdjustIn(BaseModel):
    novo_saldo: int = Field(ge=0)
    motivo: str = ""


class MovementLineIn(BaseModel):
    item_id: uuid.UUID | None = None
    novo: bool = False
    peca: str = ""            # nome, usado quando novo=True ou para achar por nome
    quantidade: int = Field(gt=0)
    categoria_id: uuid.UUID | None = None
    unidade: str = "un"
    estoque_minimo: int = Field(default=0, ge=0)
    observacoes: str = ""
    detalhes: str = ""


class MovementBatchIn(BaseModel):
    tipo: MovementType
    referencia: str = ""
    tecnico_id: uuid.UUID | None = None
    itens: list[MovementLineIn] = Field(min_length=1)


class MovementSaldoOut(BaseModel):
    item_id: uuid.UUID
    nome: str
    saldo: int


class MovementResultOut(BaseModel):
    registros: int
    novas_pecas: int
    saldos: list[MovementSaldoOut]


class HistoryLineOut(BaseModel):
    id: uuid.UUID
    data: UTCDateTime
    tipo: MovementType
    sinal: int
    quantidade: int
    tecnico: str
    referencia: str
    detalhes: str
    saldo_resultante: int


class HistoryOut(BaseModel):
    item_id: uuid.UUID
    nome: str
    saldo: int
    minimo: int
    movimentacoes: list[HistoryLineOut]
