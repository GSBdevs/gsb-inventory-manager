from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(db: DbSession, _: CurrentUser):
    rows = await db.scalars(select(Category).order_by(Category.nome))
    return list(rows)


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(data: CategoryCreate, db: DbSession, _: CurrentUser):
    category = Category(
        nome=data.nome.strip(), parent_id=data.parent_id, descricao=data.descricao.strip()
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
