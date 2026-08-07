from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession, stmt: Select, page: int = 1, size: int = 20
) -> dict[str, Any]:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = (await db.scalars(stmt.offset((page - 1) * size).limit(size))).all()
    return {"items": rows, "total": total, "page": page, "size": size}
