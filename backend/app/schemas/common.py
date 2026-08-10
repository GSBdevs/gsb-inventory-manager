from datetime import UTC, datetime
from typing import Annotated, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")


def _ensure_utc(value: datetime) -> str:
    """SQLite devolve datetime naive; sem tzinfo o JSON sai sem offset e o browser
    exibe com erro de fuso. Assume UTC quando naive e serializa com offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


UTCDateTime = Annotated[datetime, PlainSerializer(_ensure_utc, return_type=str)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
