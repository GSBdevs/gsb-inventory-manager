import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class Category(TableBase):
    __tablename__ = "categories"

    nome: Mapped[str] = mapped_column(String(160), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    descricao: Mapped[str] = mapped_column(String(500), default="")
    legacy_id: Mapped[str] = mapped_column(String(40), default="", index=True)
