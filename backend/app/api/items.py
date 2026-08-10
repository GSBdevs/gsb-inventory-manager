import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.core.pagination import paginate
from app.models import Item, Movement, Technician
from app.models.movement import SINAL
from app.schemas.common import Page
from app.schemas.item import (
    AdjustIn,
    HistoryLineOut,
    HistoryOut,
    ItemCreate,
    ItemOut,
    ItemUpdate,
)
from app.services.inventory_service import adjust_balance

router = APIRouter(prefix="/items", tags=["items"])


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


@router.get("", response_model=Page[ItemOut])
async def list_items(
    db: DbSession,
    _: CurrentUser,
    q: str = "",
    include_inactive: bool = False,
    page: int = 1,
    size: int = 20,
):
    stmt = select(Item).order_by(Item.nome)
    if not include_inactive:
        stmt = stmt.where(Item.ativo.is_(True))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Item.nome.ilike(like), Item.sku.ilike(like)))
    return await paginate(db, stmt, page, size)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(data: ItemCreate, db: DbSession, _: CurrentUser):
    nome = _norm(data.nome)
    dup = await db.scalar(select(Item).where(func.lower(Item.nome) == nome.lower()))
    if dup is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f'Já existe uma peça com esse nome: "{nome}".'
        )
    item = Item(
        nome=nome,
        sku=_norm(data.sku),
        category_id=data.category_id,
        unidade=_norm(data.unidade) or "un",
        estoque_minimo=data.estoque_minimo,
        observacoes=_norm(data.observacoes),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(item_id: uuid.UUID, data: ItemUpdate, db: DbSession, _: CurrentUser):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Peça não encontrada")
    fields = data.model_dump(exclude_unset=True)
    if "nome" in fields and fields["nome"] is not None:
        nome = _norm(fields["nome"])
        dup = await db.scalar(
            select(Item).where(func.lower(Item.nome) == nome.lower(), Item.id != item_id)
        )
        if dup is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f'Já existe outra peça com esse nome: "{nome}".'
            )
        fields["nome"] = nome
    if "unidade" in fields and fields["unidade"] is not None:
        fields["unidade"] = _norm(fields["unidade"]) or "un"
    for field, value in fields.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{item_id}/history", response_model=HistoryOut)
async def item_history(item_id: uuid.UUID, db: DbSession, _: CurrentUser):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Peça não encontrada")
    techs = {t.id: t.nome for t in await db.scalars(select(Technician))}
    movs = await db.scalars(
        select(Movement).where(Movement.item_id == item_id).order_by(Movement.created_at.desc())
    )
    linhas = [
        HistoryLineOut(
            id=m.id,
            data=m.created_at,
            tipo=m.tipo,
            sinal=SINAL[m.tipo],
            quantidade=m.quantidade,
            tecnico=techs.get(m.tecnico_id, ""),
            referencia=m.referencia,
            detalhes=m.detalhes,
            saldo_resultante=m.saldo_resultante,
        )
        for m in movs
    ]
    return HistoryOut(
        item_id=item.id,
        nome=item.nome,
        saldo=int(item.saldo_cache or 0),
        minimo=int(item.estoque_minimo or 0),
        movimentacoes=linhas,
    )


@router.post("/{item_id}/adjust", response_model=ItemOut)
async def adjust_item(item_id: uuid.UUID, data: AdjustIn, db: DbSession, user: CurrentUser):
    try:
        await adjust_balance(db, item_id, data.novo_saldo, data.motivo, user.email)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    item = await db.get(Item, item_id)
    return item
