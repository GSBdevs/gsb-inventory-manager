import uuid

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class Item(TableBase):
    __tablename__ = "items"

    sku: Mapped[str] = mapped_column(String(80), default="")
    nome: Mapped[str] = mapped_column(String(200), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    unidade: Mapped[str] = mapped_column(String(20), default="un")
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0)
    saldo_cache: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacoes: Mapped[str] = mapped_column(String(500), default="")
    legacy_id: Mapped[str] = mapped_column(String(40), default="", index=True)
