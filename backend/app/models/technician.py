from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class Technician(TableBase):
    """Técnico a quem uma movimentação é atribuída (distinto do usuário logado)."""

    __tablename__ = "technicians"

    nome: Mapped[str] = mapped_column(String(160), index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    legacy_id: Mapped[str] = mapped_column(String(40), default="", index=True)
