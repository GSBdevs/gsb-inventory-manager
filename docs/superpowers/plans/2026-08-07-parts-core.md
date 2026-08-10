# Fase 2 — Núcleo de Peças (backend) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the event-sourced parts inventory backend — categories, technicians, items, and an append-only movement ledger whose balance is derived — porting the business rules from the Apps Script `Servicos.gs`/`back.gs`.

**Architecture:** New SQLAlchemy models (`Category`, `Technician`, `Item`, `Movement`) on the existing `TableBase`. Balance is derived from the immutable `movements` ledger; `items.saldo_cache` is a recomputable optimization. Writes go through `inventory_service` which locks the affected item rows (`SELECT ... FOR UPDATE`, a no-op on SQLite but a real row lock on Postgres/Supabase), validates availability before writing, appends ledger rows, and updates the cache in one transaction. FastAPI routers stay thin; auth reuses the foundation (`require_roles`, `CurrentUser`).

**Tech Stack:** Same as the foundation — FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, pytest (SQLite in-memory). No new dependencies.

## Global Constraints

- Product language pt-BR (UI strings/errors/docs); code identifiers and commits English (conventional commits).
- Python ≥3.12; ruff `line-length = 100`, `target-version = "py312"`.
- All tables inherit `TableBase` (UUID PK + `created_at`/`updated_at`).
- Enums via `Enum(..., native_enum=False)` / `StrEnum`.
- Movement types are exactly `ENTRADA`, `SAIDA`, `AJUSTE_POS`, `AJUSTE_NEG`.
- The `movements` table is **append-only** — never update or delete a ledger row. Corrections are new `AJUSTE_*` rows.
- Balance is derived; `items.saldo_cache` is only a cache. A `SAIDA` must never drive a balance negative.
- Quantities are integers > 0 (movements) / ≥ 0 (adjust target). Sanity ceiling `QTD_MAX = 1_000_000`.
- Status thresholds (`status_do_saldo`): `saldo <= 0` → "Em falta"; `0 < saldo < minimo` → "Ruim"; `minimo <= saldo < 2*minimo` → "Alerta"; else "Bom" (with `minimo == 0`, any positive saldo is "Bom").
- Item name uniqueness is case/whitespace-insensitive (normalize before compare). Renaming an item never touches the ledger (it references `item_id`).
- Every write path requires an authenticated user; mutations use `CurrentUser`. `registrado_por` stores the operator's email (`CurrentUser.email`); `tecnico_id` is the technician the movement is attributed to (required for ENTRADA/SAIDA, null for adjustments).
- Tests: SQLite in-memory, mint Supabase-format JWTs via `tests/helpers.py` (already exists). Reuse `conftest.py` fixtures.

---

## File Structure

```
backend/app/
  models/
    category.py        # Category
    technician.py      # Technician
    item.py            # Item
    movement.py        # Movement, MovementType
    __init__.py        # + exports
  schemas/
    category.py        # CategoryCreate/Out
    technician.py      # TechnicianCreate/Out
    item.py            # ItemCreate/ItemUpdate/ItemOut, AdjustIn, MovementLineIn, MovementBatchIn, HistoryOut
  services/
    inventory_service.py   # register_movement, adjust_balance, status_do_saldo, _normalizar
  api/
    categories.py      # GET/POST /categories
    technicians.py     # GET/POST /technicians
    items.py           # GET/POST/PATCH /items, GET /items/{id}/history, POST /items/{id}/adjust
    movements.py       # POST /movements
    router.py          # + include the 4 routers
  tests/
    test_categories.py
    test_items.py
    test_movements.py
```

---

### Task 1: Category & Technician models, schemas, routers, tests

**Files:**
- Create: `backend/app/models/category.py`, `backend/app/models/technician.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/category.py`, `backend/app/schemas/technician.py`
- Create: `backend/app/api/categories.py`, `backend/app/api/technicians.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_categories.py`

**Interfaces:**
- Consumes: `TableBase` (foundation), `DbSession`/`require_roles`/`CurrentUser` (`app.core.deps`), `paginate`, `Page`, `UTCDateTime`.
- Produces: `Category` (`id, nome, parent_id, descricao, legacy_id`), `Technician` (`id, nome, ativo, legacy_id`); routers `GET/POST /api/v1/categories`, `GET/POST /api/v1/technicians`; schemas `CategoryCreate/CategoryOut`, `TechnicianCreate/TechnicianOut`.

- [ ] **Step 1: Create `backend/app/models/category.py`**

```python
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
```

- [ ] **Step 2: Create `backend/app/models/technician.py`**

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class Technician(TableBase):
    """Técnico a quem uma movimentação é atribuída (distinto do usuário logado)."""

    __tablename__ = "technicians"

    nome: Mapped[str] = mapped_column(String(160), index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    legacy_id: Mapped[str] = mapped_column(String(40), default="", index=True)
```

- [ ] **Step 3: Update `backend/app/models/__init__.py`** (add the two models to the existing exports)

```python
from app.models.base import Base, TableBase, utcnow
from app.models.category import Category
from app.models.profile import Profile, UserRole
from app.models.technician import Technician

__all__ = [
    "Base",
    "TableBase",
    "utcnow",
    "Profile",
    "UserRole",
    "Category",
    "Technician",
]
```

- [ ] **Step 4: Create `backend/app/schemas/category.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class CategoryCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    parent_id: uuid.UUID | None = None
    descricao: str = ""


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    parent_id: uuid.UUID | None
    descricao: str
    created_at: UTCDateTime
```

- [ ] **Step 5: Create `backend/app/schemas/technician.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field


class TechnicianCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)


class TechnicianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    ativo: bool
```

- [ ] **Step 6: Create `backend/app/api/categories.py`**

```python
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
```

- [ ] **Step 7: Create `backend/app/api/technicians.py`**

```python
from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Technician
from app.schemas.technician import TechnicianCreate, TechnicianOut

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("", response_model=list[TechnicianOut])
async def list_technicians(db: DbSession, _: CurrentUser):
    rows = await db.scalars(
        select(Technician).where(Technician.ativo.is_(True)).order_by(Technician.nome)
    )
    return list(rows)


@router.post("", response_model=TechnicianOut, status_code=201)
async def create_technician(data: TechnicianCreate, db: DbSession, _: CurrentUser):
    tech = Technician(nome=data.nome.strip())
    db.add(tech)
    await db.commit()
    await db.refresh(tech)
    return tech
```

- [ ] **Step 8: Register the routers** — update `backend/app/api/router.py`

```python
from fastapi import APIRouter

from app.api import auth, categories, technicians, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(technicians.router)
```

- [ ] **Step 9: Write the tests** — `backend/tests/test_categories.py`

```python
from tests.helpers import auth_headers

USER = "11111111-1111-1111-1111-111111111111"


async def test_create_and_list_category(client):
    created = await client.post(
        "/api/v1/categories", headers=auth_headers(sub=USER), json={"nome": "Cilindros"}
    )
    assert created.status_code == 201
    assert created.json()["nome"] == "Cilindros"

    listing = await client.get("/api/v1/categories", headers=auth_headers(sub=USER))
    assert listing.status_code == 200
    assert [c["nome"] for c in listing.json()] == ["Cilindros"]


async def test_create_and_list_technician(client):
    created = await client.post(
        "/api/v1/technicians", headers=auth_headers(sub=USER), json={"nome": "João"}
    )
    assert created.status_code == 201
    assert created.json()["ativo"] is True

    listing = await client.get("/api/v1/technicians", headers=auth_headers(sub=USER))
    assert [t["nome"] for t in listing.json()] == ["João"]


async def test_categories_require_auth(client):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 401
```

- [ ] **Step 10: Run tests (RED then GREEN)**

RED first (routes/models absent): after writing Step 9 but before Steps 1–8, `cd backend && .venv/Scripts/python -m pytest tests/test_categories.py -v` fails (404/import error). Implement Steps 1–8, then rerun.
GREEN: `cd backend && .venv/Scripts/python -m pytest tests/test_categories.py -v` → 3 passed. Then run the whole suite `-q` → all still pass.

- [ ] **Step 11: Commit**

```bash
git add backend/app/models/category.py backend/app/models/technician.py backend/app/models/__init__.py backend/app/schemas/category.py backend/app/schemas/technician.py backend/app/api/categories.py backend/app/api/technicians.py backend/app/api/router.py backend/tests/test_categories.py
git commit -m "feat(backend): category and technician models with CRUD"
```

---

### Task 2: Item model, schemas, items CRUD router, tests

**Files:**
- Create: `backend/app/models/item.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/item.py`
- Create: `backend/app/api/items.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_items.py`

**Interfaces:**
- Consumes: `TableBase`, `DbSession`, `CurrentUser`, `paginate`, `Page`, `UTCDateTime`, `Category`.
- Produces: `Item` (`id, sku, nome, category_id, unidade, estoque_minimo, saldo_cache, ativo, observacoes, legacy_id`); schemas `ItemCreate`, `ItemUpdate`, `ItemOut` (includes computed `status`), `AdjustIn`; routers `GET /api/v1/items` (search `q`, `status` filter, paginated), `POST`, `PATCH /items/{id}`. (History + adjust endpoints are added in Task 5, which owns the service.)

- [ ] **Step 1: Create `backend/app/models/item.py`**

```python
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
```

- [ ] **Step 2: Update `backend/app/models/__init__.py`** (add `Item`)

```python
from app.models.base import Base, TableBase, utcnow
from app.models.category import Category
from app.models.item import Item
from app.models.profile import Profile, UserRole
from app.models.technician import Technician

__all__ = [
    "Base",
    "TableBase",
    "utcnow",
    "Profile",
    "UserRole",
    "Category",
    "Technician",
    "Item",
]
```

- [ ] **Step 3: Create `backend/app/schemas/item.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field

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


class AdjustIn(BaseModel):
    novo_saldo: int = Field(ge=0)
    motivo: str = ""
```

- [ ] **Step 4: Create `backend/app/api/items.py`** (CRUD only; history/adjust routes come in Task 5)

```python
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.core.pagination import paginate
from app.models import Item
from app.schemas.common import Page
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate

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
        raise HTTPException(status.HTTP_409_CONFLICT, f'Já existe uma peça com esse nome: "{nome}".')
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
```

- [ ] **Step 5: Register the router** — update `backend/app/api/router.py`

```python
from fastapi import APIRouter

from app.api import auth, categories, items, technicians, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(technicians.router)
api_router.include_router(items.router)
```

- [ ] **Step 6: Write the tests** — `backend/tests/test_items.py`

```python
from tests.helpers import auth_headers

USER = "11111111-1111-1111-1111-111111111111"


async def test_create_item_defaults_and_lists(client):
    created = await client.post(
        "/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "Cilindro OPC"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["unidade"] == "un"
    assert body["saldo"] == 0

    listing = await client.get("/api/v1/items", headers=auth_headers(sub=USER))
    assert listing.json()["total"] == 1


async def test_create_item_rejects_duplicate_name_case_insensitive(client):
    await client.post("/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "Cilindro OPC"})
    dup = await client.post(
        "/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "  cilindro   opc "}
    )
    assert dup.status_code == 409


async def test_update_item_rename(client):
    created = await client.post(
        "/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "Fusor"}
    )
    item_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/items/{item_id}",
        headers=auth_headers(sub=USER),
        json={"nome": "Fusor A3", "estoque_minimo": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Fusor A3"
    assert resp.json()["estoque_minimo"] == 5


async def test_search_filters_by_name(client):
    for nome in ["Cilindro", "Fusor", "Correia"]:
        await client.post("/api/v1/items", headers=auth_headers(sub=USER), json={"nome": nome})
    resp = await client.get("/api/v1/items", headers=auth_headers(sub=USER), params={"q": "fus"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["nome"] == "Fusor"
```

- [ ] **Step 7: Run tests (RED then GREEN)**

RED: with the test file present but item routes absent, `pytest tests/test_items.py -v` fails. Implement Steps 1–5, rerun → 4 passed. Then whole suite `-q` → all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/item.py backend/app/models/__init__.py backend/app/schemas/item.py backend/app/api/items.py backend/app/api/router.py backend/tests/test_items.py
git commit -m "feat(backend): item model with CRUD, search and duplicate-name guard"
```

---

### Task 3: Movement model + MovementType + movement schemas

**Files:**
- Create: `backend/app/models/movement.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/item.py` (append movement/history schemas)

**Interfaces:**
- Consumes: `TableBase`.
- Produces: `MovementType` (`ENTRADA`, `SAIDA`, `AJUSTE_POS`, `AJUSTE_NEG`), `Movement` (`id, tipo, item_id, quantidade, tecnico_id, referencia, detalhes, registrado_por, saldo_resultante, estorno_de, legacy_id`); schemas `MovementLineIn`, `MovementBatchIn`, `MovementResultOut`, `HistoryLineOut`, `HistoryOut`.

- [ ] **Step 1: Create `backend/app/models/movement.py`**

```python
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
```

- [ ] **Step 2: Update `backend/app/models/__init__.py`** (add `Movement`, `MovementType`)

```python
from app.models.base import Base, TableBase, utcnow
from app.models.category import Category
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.profile import Profile, UserRole
from app.models.technician import Technician

__all__ = [
    "Base",
    "TableBase",
    "utcnow",
    "Profile",
    "UserRole",
    "Category",
    "Technician",
    "Item",
    "Movement",
    "MovementType",
]
```

- [ ] **Step 3: Append movement/history schemas to `backend/app/schemas/item.py`**

Add these classes at the end of the file (keep existing imports; add `from app.models.movement import MovementType` and `from datetime import datetime` if not present):

```python
from datetime import datetime  # noqa: E402  (add near the top with the other imports)

from app.models.movement import MovementType  # noqa: E402  (add near the top)


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
```

- [ ] **Step 4: Verify import + model registration**

Run: `cd backend && .venv/Scripts/python -c "import app.models, app.schemas.item; print(app.models.MovementType.ENTRADA)"`
Expected: prints `MovementType.ENTRADA` (import clean).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/movement.py backend/app/models/__init__.py backend/app/schemas/item.py
git commit -m "feat(backend): movement ledger model and movement/history schemas"
```

---

### Task 4: inventory_service — register_movement, adjust_balance, status helper

**Files:**
- Create: `backend/app/services/inventory_service.py`
- Create: `backend/tests/test_movements.py` (service-level tests via the API come in Task 5; this task unit-tests the pure helper and the service against a DB session)

**Interfaces:**
- Consumes: `Item`, `Movement`, `MovementType`, `SINAL`, `Technician` (models); an `AsyncSession`.
- Produces:
  - `status_do_saldo(saldo: int, minimo: int) -> str`
  - `QTD_MAX = 1_000_000`
  - `async def register_movement(db, tipo: MovementType, batch: dict, operador: str) -> dict` — batch ENTRADA/SAIDA; validates, locks items with `with_for_update()`, derives balances, blocks oversell, creates new items on ENTRADA+novo, appends ledger rows, updates `saldo_cache`. Returns `{registros, novas_pecas, saldos:[{item_id,nome,saldo}]}`.
  - `async def adjust_balance(db, item_id, novo_saldo: int, motivo: str, operador: str) -> dict` — appends one `AJUSTE_POS/NEG`, updates cache. Returns `{alterado, saldo_anterior, saldo, delta, tipo}`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_movements.py` (service-level, uses the `db_session` fixture)

```python
import uuid

import pytest

from app.models import Item, Movement, MovementType, Technician
from app.services.inventory_service import (
    adjust_balance,
    register_movement,
    status_do_saldo,
)


def test_status_thresholds():
    assert status_do_saldo(0, 5) == "Em falta"
    assert status_do_saldo(3, 5) == "Ruim"
    assert status_do_saldo(7, 5) == "Alerta"
    assert status_do_saldo(20, 5) == "Bom"
    assert status_do_saldo(1, 0) == "Bom"


async def _tecnico(db) -> uuid.UUID:
    t = Technician(nome="João")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t.id


async def test_entrada_creates_new_item_and_sets_balance(db_session):
    tid = await _tecnico(db_session)
    result = await register_movement(
        db_session,
        MovementType.ENTRADA,
        {"tecnico_id": tid, "referencia": "NF 1",
         "itens": [{"novo": True, "peca": "Cilindro", "quantidade": 10}]},
        "op@gruposb.com",
    )
    assert result["registros"] == 1
    assert result["novas_pecas"] == 1
    assert result["saldos"][0]["saldo"] == 10


async def test_saida_reduces_balance(db_session):
    tid = await _tecnico(db_session)
    await register_movement(
        db_session, MovementType.ENTRADA,
        {"tecnico_id": tid, "itens": [{"novo": True, "peca": "Fusor", "quantidade": 8}]},
        "op@gruposb.com",
    )
    item = (await db_session.scalars(__import__("sqlalchemy").select(Item))).first()
    result = await register_movement(
        db_session, MovementType.SAIDA,
        {"tecnico_id": tid, "itens": [{"item_id": item.id, "quantidade": 3}]},
        "op@gruposb.com",
    )
    assert result["saldos"][0]["saldo"] == 5


async def test_saida_blocks_oversell(db_session):
    tid = await _tecnico(db_session)
    await register_movement(
        db_session, MovementType.ENTRADA,
        {"tecnico_id": tid, "itens": [{"novo": True, "peca": "Correia", "quantidade": 2}]},
        "op@gruposb.com",
    )
    from sqlalchemy import select
    item = (await db_session.scalars(select(Item))).first()
    with pytest.raises(ValueError, match="insuficiente"):
        await register_movement(
            db_session, MovementType.SAIDA,
            {"tecnico_id": tid, "itens": [{"item_id": item.id, "quantidade": 5}]},
            "op@gruposb.com",
        )


async def test_adjust_creates_ledger_entry(db_session):
    tid = await _tecnico(db_session)
    await register_movement(
        db_session, MovementType.ENTRADA,
        {"tecnico_id": tid, "itens": [{"novo": True, "peca": "Rolo", "quantidade": 4}]},
        "op@gruposb.com",
    )
    from sqlalchemy import select
    item = (await db_session.scalars(select(Item))).first()
    result = await adjust_balance(db_session, item.id, 10, "inventário", "op@gruposb.com")
    assert result["alterado"] is True
    assert result["saldo"] == 10
    movs = (await db_session.scalars(select(Movement).where(Movement.item_id == item.id))).all()
    assert any(m.tipo == MovementType.AJUSTE_POS for m in movs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_movements.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.inventory_service`.

- [ ] **Step 3: Create `backend/app/services/inventory_service.py`**

```python
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item, Movement, MovementType, Technician
from app.models.movement import SINAL

QTD_MAX = 1_000_000


def _norm(text) -> str:
    return " ".join(str(text or "").split()).strip()


def status_do_saldo(saldo: int, minimo: int) -> str:
    saldo = int(saldo or 0)
    minimo = int(minimo or 0)
    if saldo <= 0:
        return "Em falta"
    if minimo > 0 and saldo < minimo:
        return "Ruim"
    if minimo > 0 and saldo < minimo * 2:
        return "Alerta"
    return "Bom"


def _validar_qtd(valor, contexto: str, permitir_zero: bool = False) -> int:
    try:
        q = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Quantidade inválida ({contexto}).") from None
    if q != float(valor):
        raise ValueError(f"A quantidade deve ser inteira ({contexto}).")
    if q < (0 if permitir_zero else 1):
        raise ValueError(f"Quantidade fora do permitido ({contexto}).")
    if q > QTD_MAX:
        raise ValueError("Quantidade acima do limite.")
    return q


async def register_movement(
    db: AsyncSession, tipo: MovementType, batch: dict, operador: str
) -> dict:
    if tipo not in (MovementType.ENTRADA, MovementType.SAIDA):
        raise ValueError("Tipo de movimentação inválido.")
    linhas = batch.get("itens") or []
    if not linhas:
        raise ValueError("Adicione pelo menos uma peça.")

    tecnico_id = batch.get("tecnico_id")
    if tecnico_id is not None:
        tecnico = await db.get(Technician, tecnico_id)
        if tecnico is None:
            raise ValueError("Selecione um técnico válido.")
    else:
        raise ValueError("Selecione um técnico.")

    referencia = _norm(batch.get("referencia"))
    sinal = SINAL[tipo]

    saldo_final: dict[uuid.UUID, int] = {}
    nome_do_item: dict[uuid.UUID, str] = {}
    novos = 0
    movimentos: list[Movement] = []

    for linha in linhas:
        q = _validar_qtd(linha.get("quantidade"), _norm(linha.get("peca")) or "item")
        item: Item | None = None

        if tipo == MovementType.ENTRADA and linha.get("novo"):
            nome = _norm(linha.get("peca"))
            if not nome:
                raise ValueError("Informe o nome da nova peça.")
            existe = await db.scalar(select(Item).where(func.lower(Item.nome) == nome.lower()))
            if existe is not None:
                raise ValueError(f'A peça "{nome}" já existe. Desmarque "Item novo".')
            item = Item(
                nome=nome,
                category_id=linha.get("categoria_id"),
                unidade=_norm(linha.get("unidade")) or "un",
                estoque_minimo=int(linha.get("estoque_minimo") or 0),
                observacoes=_norm(linha.get("observacoes")),
                saldo_cache=0,
            )
            db.add(item)
            await db.flush()  # garante item.id
            novos += 1
        else:
            item_id = linha.get("item_id")
            if item_id is None:
                nome = _norm(linha.get("peca"))
                item = await db.scalar(select(Item).where(func.lower(Item.nome) == nome.lower()))
            else:
                item = await db.scalar(
                    select(Item).where(Item.id == item_id).with_for_update()
                )
            if item is None:
                raise ValueError(
                    f'Peça não encontrada no estoque: "{linha.get("peca") or linha.get("item_id")}".'
                )

        atual = saldo_final.get(item.id, int(item.saldo_cache or 0))
        if tipo == MovementType.SAIDA and q > atual:
            raise ValueError(
                f'Quantidade insuficiente para "{item.nome}" '
                f"(disponível: {atual}, solicitado: {q})."
            )
        novo_saldo = atual + sinal * q
        saldo_final[item.id] = novo_saldo
        nome_do_item[item.id] = item.nome

        movimentos.append(
            Movement(
                tipo=tipo,
                item_id=item.id,
                quantidade=q,
                tecnico_id=tecnico_id,
                referencia=referencia,
                detalhes=_norm(linha.get("detalhes")),
                registrado_por=operador,
                saldo_resultante=novo_saldo,
            )
        )

    for mov in movimentos:
        db.add(mov)
    for item_id, saldo in saldo_final.items():
        item = await db.get(Item, item_id)
        item.saldo_cache = saldo

    await db.commit()
    return {
        "registros": len(movimentos),
        "novas_pecas": novos,
        "saldos": [
            {"item_id": iid, "nome": nome_do_item[iid], "saldo": s}
            for iid, s in saldo_final.items()
        ],
    }


async def adjust_balance(
    db: AsyncSession, item_id: uuid.UUID, novo_saldo: int, motivo: str, operador: str
) -> dict:
    item = await db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if item is None:
        raise ValueError("Item não encontrado.")
    alvo = _validar_qtd(novo_saldo, item.nome, permitir_zero=True)
    atual = int(item.saldo_cache or 0)
    delta = alvo - atual
    if delta == 0:
        return {"alterado": False, "saldo": atual, "message": "Saldo já estava correto."}
    tipo = MovementType.AJUSTE_POS if delta > 0 else MovementType.AJUSTE_NEG
    db.add(
        Movement(
            tipo=tipo,
            item_id=item.id,
            quantidade=abs(delta),
            tecnico_id=None,
            referencia=_norm(motivo) or "ajuste de saldo",
            registrado_por=operador,
            saldo_resultante=alvo,
        )
    )
    item.saldo_cache = alvo
    await db.commit()
    return {
        "alterado": True,
        "saldo_anterior": atual,
        "saldo": alvo,
        "delta": delta,
        "tipo": tipo,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_movements.py -v`
Expected: 5 passed (status thresholds, entrada+new item, saida reduces, oversell blocked, adjust).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/inventory_service.py backend/tests/test_movements.py
git commit -m "feat(backend): inventory service — ledger movements, derived balance, oversell guard, adjust"
```

---

### Task 5: Movements/adjust/history API routes + tests

**Files:**
- Create: `backend/app/api/movements.py`
- Modify: `backend/app/api/items.py` (add `GET /items/{id}/history` and `POST /items/{id}/adjust`)
- Modify: `backend/app/api/router.py`
- Modify: `backend/tests/test_movements.py` (append API-level tests)

**Interfaces:**
- Consumes: `register_movement`, `adjust_balance` (Task 4); `Item`, `Movement`, `Technician` (models); `CurrentUser` (its `.email` is the operator); schemas `MovementBatchIn`, `MovementResultOut`, `AdjustIn`, `HistoryOut`.
- Produces: `POST /api/v1/movements`; `POST /api/v1/items/{id}/adjust`; `GET /api/v1/items/{id}/history`.

- [ ] **Step 1: Create `backend/app/api/movements.py`**

```python
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.item import MovementBatchIn, MovementResultOut
from app.services.inventory_service import register_movement

router = APIRouter(prefix="/movements", tags=["movements"])


@router.post("", response_model=MovementResultOut, status_code=status.HTTP_201_CREATED)
async def create_movement(data: MovementBatchIn, db: DbSession, user: CurrentUser):
    try:
        return await register_movement(
            db, data.tipo, data.model_dump(), user.email
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
```

- [ ] **Step 2: Add history + adjust routes to `backend/app/api/items.py`**

Add these imports near the top: `from app.models import Movement, Technician` and `from app.schemas.item import AdjustIn, HistoryLineOut, HistoryOut` and `from app.models.movement import SINAL` and `from app.services.inventory_service import adjust_balance`. Then append:

```python
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
```

- [ ] **Step 3: Register the movements router** — update `backend/app/api/router.py`

```python
from fastapi import APIRouter

from app.api import auth, categories, items, movements, technicians, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(technicians.router)
api_router.include_router(items.router)
api_router.include_router(movements.router)
```

- [ ] **Step 4: Append API-level tests to `backend/tests/test_movements.py`**

```python
from tests.helpers import auth_headers

_U = "11111111-1111-1111-1111-111111111111"


async def _make_tecnico(client) -> str:
    r = await client.post("/api/v1/technicians", headers=auth_headers(sub=_U), json={"nome": "Ana"})
    return r.json()["id"]


async def test_api_entrada_then_saida_then_history(client):
    tid = await _make_tecnico(client)
    entrada = await client.post(
        "/api/v1/movements",
        headers=auth_headers(sub=_U),
        json={"tipo": "ENTRADA", "tecnico_id": tid,
              "itens": [{"novo": True, "peca": "Cilindro", "quantidade": 10}]},
    )
    assert entrada.status_code == 201
    assert entrada.json()["saldos"][0]["saldo"] == 10

    items = await client.get("/api/v1/items", headers=auth_headers(sub=_U))
    item_id = items.json()["items"][0]["id"]

    saida = await client.post(
        "/api/v1/movements",
        headers=auth_headers(sub=_U),
        json={"tipo": "SAIDA", "tecnico_id": tid,
              "itens": [{"item_id": item_id, "quantidade": 4}]},
    )
    assert saida.status_code == 201
    assert saida.json()["saldos"][0]["saldo"] == 6

    hist = await client.get(f"/api/v1/items/{item_id}/history", headers=auth_headers(sub=_U))
    assert hist.status_code == 200
    body = hist.json()
    assert body["saldo"] == 6
    assert len(body["movimentacoes"]) == 2
    assert body["movimentacoes"][0]["tipo"] == "SAIDA"  # mais recente primeiro


async def test_api_oversell_returns_400(client):
    tid = await _make_tecnico(client)
    await client.post(
        "/api/v1/movements", headers=auth_headers(sub=_U),
        json={"tipo": "ENTRADA", "tecnico_id": tid,
              "itens": [{"novo": True, "peca": "Correia", "quantidade": 2}]},
    )
    items = await client.get("/api/v1/items", headers=auth_headers(sub=_U))
    item_id = items.json()["items"][0]["id"]
    resp = await client.post(
        "/api/v1/movements", headers=auth_headers(sub=_U),
        json={"tipo": "SAIDA", "tecnico_id": tid,
              "itens": [{"item_id": item_id, "quantidade": 9}]},
    )
    assert resp.status_code == 400
    assert "insuficiente" in resp.json()["detail"].lower()


async def test_api_adjust_updates_balance(client):
    tid = await _make_tecnico(client)
    await client.post(
        "/api/v1/movements", headers=auth_headers(sub=_U),
        json={"tipo": "ENTRADA", "tecnico_id": tid,
              "itens": [{"novo": True, "peca": "Rolo", "quantidade": 4}]},
    )
    items = await client.get("/api/v1/items", headers=auth_headers(sub=_U))
    item_id = items.json()["items"][0]["id"]
    resp = await client.post(
        f"/api/v1/items/{item_id}/adjust", headers=auth_headers(sub=_U),
        json={"novo_saldo": 10, "motivo": "inventário"},
    )
    assert resp.status_code == 200
    assert resp.json()["saldo"] == 10
```

- [ ] **Step 5: Run the whole suite (GREEN)**

Run: `cd backend && .venv/Scripts/python -m pytest -q`
Expected: all pass (foundation + categories + items + movements service + movements API).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/movements.py backend/app/api/items.py backend/app/api/router.py backend/tests/test_movements.py
git commit -m "feat(backend): movement/adjust/history endpoints over the inventory service"
```

---

### Task 6: Alembic migration for the new tables + full verification

**Files:**
- Create: a new migration under `backend/alembic/versions/`

**Interfaces:**
- Consumes: all Task 1–5 models.
- Produces: a migration creating `categories`, `technicians`, `items`, `movements` (on top of the `profiles` baseline).

- [ ] **Step 1: Autogenerate the migration against a scratch SQLite DB**

Run (bash):
```bash
cd backend && DATABASE_URL="sqlite+aiosqlite:///./_scratch.db" .venv/Scripts/python -m alembic upgrade head
cd backend && DATABASE_URL="sqlite+aiosqlite:///./_scratch.db" .venv/Scripts/python -m alembic revision --autogenerate -m "parts core: categories, technicians, items, movements"
rm -f backend/_scratch.db
```
Open the generated file and CONFIRM `upgrade()` creates all four tables (`categories`, `technicians`, `items`, `movements`) with the FK from `movements.item_id` → `items.id`. If it is empty, the models weren't imported — STOP and report BLOCKED.

- [ ] **Step 2: Verify the full migration chain applies from scratch**

Run (bash):
```bash
cd backend && DATABASE_URL="sqlite+aiosqlite:///./_verify.db" .venv/Scripts/python -m alembic upgrade head && rm -f backend/_verify.db
```
Expected: applies `profiles` baseline then the new revision, no errors.

- [ ] **Step 3: Full test suite + lint**

Run: `cd backend && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .`
Expected: all tests pass; ruff clean (the new migration is excluded via the `alembic/versions` exclude from the foundation).

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions
git commit -m "feat(backend): migration for categories, technicians, items and movements"
```

---

## Self-Review

**1. Spec coverage (design spec §2 rules, §4 items/movements/categories, §5 movements/items/adjust/history API):**
- Category/Item/Movement models + Technician (source-system entity) → Tasks 1–3. ✓
- Event-sourced ledger, derived balance, oversell guard, `SELECT FOR UPDATE`, on-the-fly item on ENTRADA, adjust → ledger, status thresholds (§2) → Task 4. ✓
- Items CRUD with case-insensitive unique name; rename doesn't touch ledger (ledger uses `item_id`) (§2) → Task 2. ✓
- `POST /movements`, `POST /items/{id}/adjust`, `GET /items/{id}/history`, categories/technicians endpoints (§5) → Tasks 1, 5. ✓
- Migration for the new tables (§10 phase 2) → Task 6. ✓
- Reports/alerts and machines are **out of scope** (spec §10 phases 3–4, own plans). The parts **frontend** (itens/movimentar/history pages) is a follow-on plan.

**2. Placeholder scan:** No TBD/"add validation". Every step has concrete code, exact commands, expected outputs.

**3. Type consistency:** `MovementType` values match across model, `SINAL`, schemas, and tests. `register_movement`/`adjust_balance` signatures in Task 4 match the calls in Task 5. `ItemOut.saldo` aliases `saldo_cache` consistently. `with_for_update()` used on the item read in both service functions (no-op on SQLite, real lock on Postgres). Technician required for ENTRADA/SAIDA, null for adjust — enforced in `register_movement` and left null in `adjust_balance`.
