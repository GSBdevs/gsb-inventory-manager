import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class MovementType(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE_POS = "AJUSTE_POS"
    AJUSTE_NEG = "AJUSTE_NEG"


SINAL = {
    MovementType.ENTRADA: 1,
    MovementType.AJUSTE_POS: 1,
    MovementType.SAIDA: -1,
    MovementType.AJUSTE_NEG: -1,
}


class Movement(TableBase):
    """Ledger imutável (append-only). NUNCA editar/apagar uma linha."""

    __tablename__ = "movements"

    tipo: Mapped[MovementType] = mapped_column(Enum(MovementType, native_enum=False, length=16))
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("items.id", ondelete="RESTRICT"), index=True
    )
    quantidade: Mapped[int] = mapped_column(Integer)
    tecnico_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    referencia: Mapped[str] = mapped_column(String(200), default="")
    detalhes: Mapped[str] = mapped_column(String(500), default="")
    registrado_por: Mapped[str] = mapped_column(String(255), default="")
    saldo_resultante: Mapped[int] = mapped_column(Integer)
    estorno_de: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    legacy_id: Mapped[str] = mapped_column(String(40), default="", index=True)
