# Fundação (Scaffold + Auth) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `inventory-manager` project skeleton — a runnable FastAPI backend with JWT/Argon2 auth and user management, plus a React/Vite/Tailwind frontend that logs in against it — mirroring the `gsb-crm` architecture.

**Architecture:** Async FastAPI + SQLAlchemy 2 (Postgres in prod, SQLite fallback in dev/tests) with a UUID+audit `TableBase`. Auth uses short-lived JWT access tokens + rotating refresh tokens (persisted for revocation) and Argon2id hashing. The React SPA talks to `/api/v1` through a single-flight refresh client and can be served single-origin by the API in production.

**Tech Stack:** Python ≥3.12, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2 + pydantic-settings, PyJWT, pwdlib[argon2], aiosqlite, psycopg[binary]. Frontend: React 19, TypeScript ~5.7, Vite 6, Tailwind 4, TanStack Query 5, react-router 7.

## Global Constraints

- Product language pt-BR (UI strings, error messages, docs). Code identifiers and commits in English (conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Python `requires-python = ">=3.12"`; ruff `line-length = 100`, `target-version = "py312"`.
- All DB tables inherit `TableBase` (UUID PK + `created_at`/`updated_at`).
- Enums stored as NAME via `Enum(..., native_enum=False)` (SQLAlchemy) / `StrEnum` (Python).
- User roles are exactly `admin` and `operador` (no others in this project).
- Dark-only theme: neutrals black/gray + primary yellow `oklch(0.83 0.16 90)`; green/red semantic only.
- Windows dev note: psycopg async needs `SelectorEventLoop` → run the API via `python run.py`, not `uvicorn app.main:app`, when using Postgres.
- With `ENV != dev` and a dev `SECRET_KEY`, the API must refuse to boot.
- API version prefix is `/api/v1`; docs at `/api/v1/docs`.
- Tests use SQLite in-memory; run with `.venv\Scripts\python -m pytest` (Windows) / `python -m pytest`.

---

## File Structure

```
inventory-manager/
  backend/
    pyproject.toml
    run.py                       # dev entrypoint (Windows Selector loop)
    .env.example
    app/
      __init__.py
      main.py                    # FastAPI app, lifespan, health, SPA mount
      core/
        __init__.py
        config.py                # Settings (pydantic-settings)
        aio.py                   # run(coro) with per-platform loop factory
        database.py              # async engine + session_factory + get_db
        security.py              # Argon2 hash + JWT create/decode
        deps.py                  # DbSession, get_current_user, require_roles
        pagination.py            # paginate(stmt) -> Page dict
      models/
        __init__.py              # exports Base, TableBase, User, ... + utcnow
        base.py                  # Base, TableBase, utcnow
        user.py                  # User, UserRole, RefreshToken
      schemas/
        __init__.py
        common.py                # UTCDateTime, Page[T]
        auth.py                  # Login/Refresh/Token/Bootstrap/User schemas
      api/
        __init__.py
        router.py                # aggregates module routers under /api/v1
        auth.py                  # login/refresh/logout/me/bootstrap
        users.py                 # admin CRUD
      services/
        __init__.py
    scripts/
      seed.py                    # admin@gruposb.com / admin123
    alembic.ini
    alembic/
      env.py
      versions/
    tests/
      conftest.py                # in-memory DB + AsyncClient fixtures
      test_security.py
      test_auth.py
      test_users.py
  frontend/
    package.json
    tsconfig.json
    tsconfig.node.json
    vite.config.ts
    index.html
    src/
      main.tsx                   # QueryClientProvider + router + AuthProvider
      App.tsx                    # routes + protected shell
      index.css                  # Tailwind 4 + theme tokens
      types.ts                   # TokenPair, User, Page<T>
      vite-env.d.ts
      lib/
        api.ts                   # fetch client + single-flight refresh
        utils.ts                 # cn()
      context/
        auth.tsx                 # AuthProvider + useAuth
      components/
        ui/                      # button, input, card, label (cva primitives)
        layout/
          app-shell.tsx          # sidebar + topbar + <Outlet/>
      pages/
        login.tsx
        dashboard.tsx            # placeholder KPIs page
  docker-compose.yml             # db(5433) + api + frontend
  serve-lan.ps1                  # build front + single-origin serve
  README.md
  CLAUDE.md
  HANDOFF.md
```

---

### Task 1: Backend skeleton — config, loop, database, base model, health

**Files:**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/run.py`
- Create: `backend/app/__init__.py`, `backend/app/main.py`
- Create: `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/aio.py`, `backend/app/core/database.py`
- Create: `backend/app/models/__init__.py`, `backend/app/models/base.py`
- Create: `backend/app/api/__init__.py`, `backend/app/api/router.py`
- Create: `backend/app/schemas/__init__.py`, `backend/app/services/__init__.py`

**Interfaces:**
- Produces: `settings` (`app.core.config`), `engine`/`session_factory`/`get_db` (`app.core.database`), `run(coro)` (`app.core.aio`), `Base`/`TableBase`/`utcnow` (`app.models.base` re-exported from `app.models`), `api_router` (`app.api.router`), `app` (`app.main`).

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "inventory-manager-backend"
version = "0.1.0"
description = "Backend do Gerenciador de Estoque do Grupo SB — FastAPI + SQLAlchemy async"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.36",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.6",
    "email-validator>=2.2",
    "pyjwt>=2.10",
    "pwdlib[argon2]>=0.2",
    "aiosqlite>=0.20",
    "psycopg[binary]>=3.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "httpx>=0.28",
    "ruff>=0.8",
]

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Create `backend/app/core/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GrupoSB Estoque"
    env: str = "dev"
    # >= 32 bytes exigidos pelo HS256; troque em produção.
    secret_key: str = "dev-secret-troque-em-producao-0000000000"

    # Bind do servidor (run.py). API_HOST=0.0.0.0 expõe na rede local.
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Caminho do build do frontend (frontend/dist). Preenchido = API serve a SPA
    # na raiz (origem única, sem CORS). Vazio = API pura (dev com Vite).
    frontend_dist: str = ""

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Rate-limit do login: nº de falhas por IP dentro da janela antes do 429.
    login_max_failures: int = 10
    login_window_seconds: int = 300

    # Default de dev: SQLite local, zero infraestrutura. Produção/Docker: Postgres.
    database_url: str = "sqlite+aiosqlite:///./estoque_dev.db"
    auto_create_tables: bool = True

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 3: Create `backend/app/core/aio.py`**

```python
"""Execução de corrotinas com o event loop correto por plataforma.

psycopg async exige SelectorEventLoop; o default do Windows é o Proactor.
loop_factory explícito (Python 3.12+) evita a API de policy (deprecada no 3.14).
"""

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

LOOP_FACTORY = asyncio.SelectorEventLoop if sys.platform == "win32" else None


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro, loop_factory=LOOP_FACTORY)
```

- [ ] **Step 4: Create `backend/app/core/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)

if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_fk_on(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
```

- [ ] **Step 5: Create `backend/app/models/base.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TableBase(Base):
    """Base comum: PK UUID + auditoria (created_at/updated_at)."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
```

- [ ] **Step 6: Create `backend/app/models/__init__.py`** (User is added in Task 3; keep exports minimal now)

```python
from app.models.base import Base, TableBase, utcnow

__all__ = ["Base", "TableBase", "utcnow"]
```

- [ ] **Step 7: Create empty package markers and the router aggregator**

`backend/app/__init__.py`: empty file.
`backend/app/core/__init__.py`: empty file.
`backend/app/schemas/__init__.py`: empty file.
`backend/app/services/__init__.py`: empty file.
`backend/app/api/__init__.py`: empty file.

`backend/app/api/router.py`:

```python
from fastapi import APIRouter

api_router = APIRouter()
```

- [ ] **Step 8: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.env != "dev" and "dev-secret" in settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY de desenvolvimento com ENV != dev. "
            'Gere uma chave: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/healthz", tags=["health"])
async def healthz():
    return {"status": "ok", "env": settings.env}


# Origem única: se frontend_dist apontar para um build, a API serve a SPA.
_dist = Path(settings.frontend_dist) if settings.frontend_dist else None
if _dist is not None and (_dist / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "healthz")):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        candidate = _dist / full_path
        if (
            full_path
            and candidate.is_file()
            and candidate.resolve().is_relative_to(_dist.resolve())
        ):
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
```

- [ ] **Step 9: Create `backend/run.py`**

```python
"""Entrypoint de desenvolvimento (Windows-safe).

psycopg async exige SelectorEventLoop, mas o uvicorn cria um Proactor antes de
importar o app no Windows. Aqui o servidor roda dentro de um loop Selector.

Uso: python run.py   (sem --reload; para hot-reload use SQLite ou docker compose)
"""

import uvicorn

from app.core.aio import run
from app.core.config import settings


async def _serve() -> None:
    config = uvicorn.Config("app.main:app", host=settings.api_host, port=settings.api_port)
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    run(_serve())
```

- [ ] **Step 10: Create `backend/.env.example`**

```dotenv
# Copie para .env e ajuste. SEM .env, o backend usa SQLite local (zero infra).
ENV=dev
# Gere: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=dev-secret-troque-em-producao-0000000000

API_HOST=127.0.0.1
API_PORT=8000

# Postgres (docker compose expõe em 5433 pois a máquina tem PG nativo em 5432):
# DATABASE_URL=postgresql+psycopg://estoque:estoque@localhost:5433/estoque
DATABASE_URL=sqlite+aiosqlite:///./estoque_dev.db
AUTO_CREATE_TABLES=true

# Origem única em produção: aponte para o build do front.
# FRONTEND_DIST=../frontend/dist
```

- [ ] **Step 11: Install and boot the API**

Run:
```bash
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
```
Then:
```bash
cd backend && .venv/Scripts/python run.py
```
Expected: server starts on `http://127.0.0.1:8000`; `GET http://127.0.0.1:8000/healthz` returns `{"status":"ok","env":"dev"}`. Stop the server (Ctrl+C) after confirming.

- [ ] **Step 12: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/run.py backend/app
git commit -m "feat(backend): project skeleton with config, async db, base model and health"
```

---

### Task 2: Security primitives (Argon2 + JWT)

**Files:**
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(plain) -> str`, `verify_password(plain, hashed) -> bool`, `create_token_pair(user_id: str) -> dict` (keys: `access_token`, `refresh_token`, `token_type`, `expires_in`, `refresh_jti`, `refresh_expires_at`), `decode_token(token, expected_type) -> dict`, `TokenType = Literal["access","refresh"]`, `ALGORITHM = "HS256"`.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_security.py`

```python
import jwt
import pytest

from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("segredo123")
    assert hashed != "segredo123"
    assert verify_password("segredo123", hashed)
    assert not verify_password("errada", hashed)


def test_token_pair_roundtrip():
    pair = create_token_pair("user-42")
    access = decode_token(pair["access_token"], "access")
    refresh = decode_token(pair["refresh_token"], "refresh")
    assert access["sub"] == "user-42"
    assert refresh["jti"] == pair["refresh_jti"]


def test_decode_rejects_wrong_type():
    pair = create_token_pair("user-42")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(pair["access_token"], "refresh")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.security'`.

- [ ] **Step 3: Create `backend/app/core/security.py`**

```python
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()  # Argon2id


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


TokenType = Literal["access", "refresh"]


def _create_token(
    subject: str, token_type: TokenType, expires_delta: timedelta, jti: str | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti or uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_token_pair(user_id: str) -> dict[str, Any]:
    """Gera o par access+refresh. O jti do refresh é exposto para persistência
    (rotação/revogação); campos extras são filtrados pelo response_model."""
    refresh_jti = uuid.uuid4().hex
    refresh_expires = timedelta(days=settings.refresh_token_expire_days)
    access = _create_token(
        user_id, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh = _create_token(user_id, "refresh", refresh_expires, jti=refresh_jti)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "refresh_jti": refresh_jti,
        "refresh_expires_at": datetime.now(timezone.utc) + refresh_expires,
    }


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decodifica e valida o token. Levanta jwt.InvalidTokenError se inválido/expirado."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"esperado token '{expected_type}'")
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_security.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat(backend): Argon2 hashing and JWT access/refresh tokens"
```

---

### Task 3: User & RefreshToken models, common + auth schemas, deps, pagination

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/common.py`, `backend/app/schemas/auth.py`
- Create: `backend/app/core/deps.py`, `backend/app/core/pagination.py`

**Interfaces:**
- Consumes: `TableBase`, `utcnow` (Task 1); `decode_token` (Task 2).
- Produces: `User` (fields: `id, email, full_name, hashed_password, role, is_active, created_at, updated_at`), `UserRole` (`ADMIN="admin"`, `OPERADOR="operador"`), `RefreshToken` (`user_id, jti, expires_at, revoked_at`); schemas `LoginIn, RefreshIn, TokenPair, BootstrapIn, UserCreate, UserUpdate, UserOut`; `UTCDateTime`, `Page[T]`; deps `DbSession`, `CurrentUser`, `get_current_user`, `require_roles`; `paginate`.

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TableBase


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERADOR = "operador"


class User(TableBase):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.OPERADOR
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshToken(TableBase):
    """Refresh tokens emitidos — habilita rotação e revogação (logout)."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Update `backend/app/models/__init__.py`**

```python
from app.models.base import Base, TableBase, utcnow
from app.models.user import RefreshToken, User, UserRole

__all__ = ["Base", "TableBase", "utcnow", "User", "UserRole", "RefreshToken"]
```

- [ ] **Step 3: Create `backend/app/schemas/common.py`**

```python
from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")


def _ensure_utc(value: datetime) -> str:
    """SQLite devolve datetime naive; sem tzinfo o JSON sai sem offset e o browser
    exibe com erro de fuso. Assume UTC quando naive e serializa com offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


UTCDateTime = Annotated[datetime, PlainSerializer(_ensure_utc, return_type=str)]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
```

- [ ] **Step 4: Create `backend/app/schemas/auth.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import UTCDateTime


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class BootstrapIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""
    role: UserRole = UserRole.OPERADOR


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: UTCDateTime
```

- [ ] **Step 5: Create `backend/app/core/pagination.py`**

```python
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
```

- [ ] **Step 6: Create `backend/app/core/deps.py`**

```python
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou ausentes",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação",
            )
        return user

    return Depends(_check)
```

- [ ] **Step 7: Verify imports resolve**

Run: `cd backend && .venv/Scripts/python -c "import app.core.deps, app.core.pagination, app.schemas.auth, app.models"`
Expected: no output, exit code 0.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/core/deps.py backend/app/core/pagination.py
git commit -m "feat(backend): user/refresh-token models, auth schemas, deps and pagination"
```

---

### Task 4: Auth router (login/refresh/logout/me/bootstrap) + rate limit + tests

**Files:**
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/conftest.py`, `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `create_token_pair, decode_token, hash_password, verify_password` (Task 2); `User, RefreshToken, UserRole, utcnow` (Task 3); `CurrentUser, DbSession` (Task 3); schemas (Task 3); `settings` (Task 1).
- Produces: router with `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/bootstrap`; test fixtures `client` (httpx AsyncClient) and `db_session`.

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture
async def _engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(_engine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write the failing test** — `backend/tests/test_auth.py`

```python
import pytest


@pytest.fixture
async def bootstrapped(client):
    resp = await client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@gruposb.com", "password": "admin123", "full_name": "Admin"},
    )
    assert resp.status_code == 201
    return resp.json()


async def test_bootstrap_creates_first_admin_then_conflicts(client):
    first = await client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@gruposb.com", "password": "admin123"},
    )
    assert first.status_code == 201
    assert "access_token" in first.json()

    second = await client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "outro@gruposb.com", "password": "admin123"},
    )
    assert second.status_code == 409


async def test_login_success_and_me(client, bootstrapped):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@gruposb.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    access = resp.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@gruposb.com"
    assert me.json()["role"] == "admin"


async def test_login_wrong_password(client, bootstrapped):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@gruposb.com", "password": "errada"},
    )
    assert resp.status_code == 401


async def test_refresh_rotates_and_revokes_old(client, bootstrapped):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@gruposb.com", "password": "admin123"},
    )
    old_refresh = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200

    # Reusar o refresh antigo (já rotacionado) deve falhar.
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: FAIL — bootstrap returns 404 (route not registered yet).

- [ ] **Step 4: Create `backend/app/api/auth.py`**

```python
import time
import uuid
from collections import defaultdict, deque

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_token_pair, decode_token, hash_password, verify_password
from app.models import RefreshToken, User, UserRole, utcnow
from app.schemas.auth import BootstrapIn, LoginIn, RefreshIn, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate-limit de login por IP, em memória (suficiente p/ 1 processo). Só falhas contam.
_login_failures: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_login_rate(ip: str) -> None:
    window = _login_failures[ip]
    cutoff = time.monotonic() - settings.login_window_seconds
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= settings.login_max_failures:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas de login — aguarde alguns minutos",
        )


def _register_login_failure(ip: str) -> None:
    _login_failures[ip].append(time.monotonic())


def _reset_login_failures(ip: str) -> None:
    _login_failures.pop(ip, None)


async def _issue_tokens(db: DbSession, user: User) -> dict:
    pair = create_token_pair(str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id, jti=pair["refresh_jti"], expires_at=pair["refresh_expires_at"]
        )
    )
    await db.commit()
    return pair


@router.post("/login", response_model=TokenPair)
async def login(data: LoginIn, db: DbSession, request: Request):
    ip = _client_ip(request)
    _check_login_rate(ip)
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.hashed_password):
        _register_login_failure(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha incorretos")
    if not user.is_active:
        _register_login_failure(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário desativado")
    _reset_login_failures(ip)
    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn, db: DbSession):
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Refresh token inválido ou expirado"
    )
    try:
        payload = decode_token(data.refresh_token, "refresh")
        user_id = uuid.UUID(payload["sub"])
        jti = payload["jti"]
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None

    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if token_row is None or token_row.revoked_at is not None:
        raise unauthorized

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    token_row.revoked_at = utcnow()  # rotação: revoga o refresh usado
    return await _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshIn, db: DbSession):
    try:
        payload = decode_token(data.refresh_token, "refresh")
        jti = payload["jti"]
    except (jwt.InvalidTokenError, KeyError):
        return
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = utcnow()
        await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/bootstrap", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def bootstrap(data: BootstrapIn, db: DbSession):
    """Cria o primeiro usuário (admin). Disponível apenas com a base vazia."""
    count = await db.scalar(select(func.count()).select_from(User))
    if count:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existem usuários cadastrados")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    return await _issue_tokens(db, user)
```

- [ ] **Step 5: Register the router** — update `backend/app/api/router.py`

```python
from fastapi import APIRouter

from app.api import auth

api_router = APIRouter()
api_router.include_router(auth.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_auth.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/auth.py backend/app/api/router.py backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "feat(backend): auth endpoints with rotating refresh and login rate limit"
```

---

### Task 5: Users admin CRUD router + tests

**Files:**
- Create: `backend/app/api/users.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_users.py`

**Interfaces:**
- Consumes: `DbSession`, `require_roles`, `get_current_user` (Task 3); `paginate` (Task 3); `hash_password` (Task 2); `User, UserRole` (Task 3); `Page`, `UserCreate, UserUpdate, UserOut` (Task 3).
- Produces: router with `GET /users` (admin, paginated), `POST /users` (admin), `PATCH /users/{id}` (admin).

- [ ] **Step 1: Write the failing test** — `backend/tests/test_users.py`

```python
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@gruposb.com", "password": "admin123", "full_name": "Admin"},
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_admin_creates_and_lists_users(client, admin_token):
    created = await client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={"email": "op@gruposb.com", "password": "op12345", "role": "operador"},
    )
    assert created.status_code == 201
    assert created.json()["role"] == "operador"

    listing = await client.get("/api/v1/users", headers=_auth(admin_token))
    assert listing.status_code == 200
    assert listing.json()["total"] == 2  # admin + operador


async def test_operador_cannot_manage_users(client, admin_token):
    await client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={"email": "op@gruposb.com", "password": "op12345", "role": "operador"},
    )
    op_login = await client.post(
        "/api/v1/auth/login", json={"email": "op@gruposb.com", "password": "op12345"}
    )
    op_token = op_login.json()["access_token"]

    resp = await client.get("/api/v1/users", headers=_auth(op_token))
    assert resp.status_code == 403


async def test_create_rejects_duplicate_email(client, admin_token):
    payload = {"email": "dup@gruposb.com", "password": "dup12345"}
    first = await client.post("/api/v1/users", headers=_auth(admin_token), json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/users", headers=_auth(admin_token), json=payload)
    assert second.status_code == 409


async def test_admin_updates_user(client, admin_token):
    created = await client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={"email": "op@gruposb.com", "password": "op12345"},
    )
    user_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=_auth(admin_token),
        json={"is_active": False, "full_name": "Operador Um"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["full_name"] == "Operador Um"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/Scripts/python -m pytest tests/test_users.py -v`
Expected: FAIL — `POST /users` returns 404.

- [ ] **Step 3: Create `backend/app/api/users.py`**

```python
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DbSession, require_roles
from app.core.pagination import paginate
from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.schemas.common import Page

router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[require_roles(UserRole.ADMIN)]
)


@router.get("", response_model=Page[UserOut])
async def list_users(db: DbSession, q: str = "", page: int = 1, size: int = 20):
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(User.email.ilike(like) | User.full_name.ilike(like))
    return await paginate(db, stmt, page, size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DbSession):
    exists = await db.scalar(select(User).where(User.email == data.email))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um usuário com esse email")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: uuid.UUID, data: UserUpdate, db: DbSession):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    fields = data.model_dump(exclude_unset=True)
    if "password" in fields:
        password = fields.pop("password")
        if password:
            user.hashed_password = hash_password(password)
    for field, value in fields.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
```

- [ ] **Step 4: Register the router** — update `backend/app/api/router.py`

```python
from fastapi import APIRouter

from app.api import auth, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/Scripts/python -m pytest -v`
Expected: all tests pass (security + auth + users).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/users.py backend/app/api/router.py backend/tests/test_users.py
git commit -m "feat(backend): admin user management endpoints"
```

---

### Task 6: Seed script + Alembic migration

**Files:**
- Create: `backend/scripts/seed.py`, `backend/scripts/__init__.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- Create: first migration under `backend/alembic/versions/`

**Interfaces:**
- Consumes: `settings`, `engine` (Task 1); `Base`, `User`, `UserRole` (Task 3); `hash_password` (Task 2); `run` (Task 1 aio).
- Produces: `seed.py` creating an admin; a baseline Alembic migration creating `users` + `refresh_tokens`.

- [ ] **Step 1: Create `backend/scripts/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/scripts/seed.py`**

```python
"""Popula a base com um admin inicial. Idempotente por email.

Uso: cd backend && .venv/Scripts/python -m scripts.seed
Credenciais: admin@gruposb.com / admin123 (troque em produção).
"""

from sqlalchemy import select

from app.core.aio import run
from app.core.database import engine, session_factory
from app.core.security import hash_password
from app.models import Base, User, UserRole

ADMIN_EMAIL = "admin@gruposb.com"
ADMIN_PASSWORD = "admin123"


async def _seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        exists = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if exists is not None:
            print(f"Admin {ADMIN_EMAIL} já existe — nada a fazer.")
            return
        db.add(
            User(
                email=ADMIN_EMAIL,
                full_name="Administrador",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
        )
        await db.commit()
        print(f"Admin criado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    await engine.dispose()


if __name__ == "__main__":
    run(_seed())
```

- [ ] **Step 3: Run the seed against SQLite**

Run: `cd backend && .venv/Scripts/python -m scripts.seed`
Expected: prints `Admin criado: admin@gruposb.com / admin123`. Running again prints `já existe`.

- [ ] **Step 4: Create `backend/alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5: Create `backend/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Create `backend/alembic/env.py`** (offline+online, sync driver derived from settings)

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 7: Autogenerate the baseline migration against a scratch SQLite DB**

Run (bash):
```bash
cd backend && DATABASE_URL="sqlite+aiosqlite:///./_scratch.db" .venv/Scripts/python -m alembic revision --autogenerate -m "baseline: users and refresh_tokens"
```
Then delete the scratch DB: `rm -f backend/_scratch.db`.
Expected: a new file in `backend/alembic/versions/` whose `upgrade()` creates `users` and `refresh_tokens`.

- [ ] **Step 8: Verify the migration applies cleanly**

Run (bash):
```bash
cd backend && DATABASE_URL="sqlite+aiosqlite:///./_verify.db" .venv/Scripts/python -m alembic upgrade head && rm -f backend/_verify.db
```
Expected: `Running upgrade -> <rev>, baseline: users and refresh_tokens`, no errors.

- [ ] **Step 9: Commit**

```bash
git add backend/scripts backend/alembic.ini backend/alembic
git commit -m "feat(backend): seed admin script and baseline alembic migration"
```

---

### Task 7: Frontend skeleton — Vite, Tailwind theme, api client, auth context

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/vite-env.d.ts`, `frontend/src/types.ts`
- Create: `frontend/src/lib/api.ts`, `frontend/src/lib/utils.ts`, `frontend/src/context/auth.tsx`

**Interfaces:**
- Produces: `api<T>(path, options)`, `setTokens/clearTokens/getAccessToken/getRefreshToken`, `ApiError` (`lib/api.ts`); `cn(...)` (`lib/utils.ts`); `AuthProvider`, `useAuth` (`context/auth.tsx`); types `TokenPair`, `User`, `UserRole`, `Page<T>` (`types.ts`).
- Consumes: backend `/api/v1/auth/*` (Task 4).

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "inventory-manager-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@radix-ui/react-label": "^2.1.1",
    "@radix-ui/react-slot": "^1.1.1",
    "@tanstack/react-query": "^5.62.7",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.469.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router": "^7.1.1",
    "sonner": "^1.7.1",
    "tailwind-merge": "^3.0.1"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@types/node": "^22.10.2",
    "@types/react": "^19.0.2",
    "@types/react-dom": "^19.0.2",
    "@vitejs/plugin-react": "^4.3.4",
    "tailwindcss": "^4.0.0",
    "tw-animate-css": "^1.2.5",
    "typescript": "~5.7.2",
    "vite": "^6.0.5"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json` and `frontend/tsconfig.node.json`**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create `frontend/vite.config.ts`**

```typescript
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
```

- [ ] **Step 4: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="pt-BR" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GrupoSB Estoque</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/src/index.css`** (theme tokens, black/gray/yellow)

```css
@import "tailwindcss";
@import "tw-animate-css";

/* Tema escuro único — preto/cinza com destaques em amarelo (tokens shadcn/ui) */
:root {
  --background: oklch(0.13 0 0);
  --foreground: oklch(0.96 0 0);
  --card: oklch(0.17 0.004 90);
  --card-foreground: oklch(0.96 0 0);
  --popover: oklch(0.19 0.004 90);
  --popover-foreground: oklch(0.96 0 0);
  --primary: oklch(0.83 0.16 90);
  --primary-foreground: oklch(0.18 0.03 90);
  --secondary: oklch(0.24 0.004 90);
  --secondary-foreground: oklch(0.92 0 0);
  --muted: oklch(0.22 0.004 90);
  --muted-foreground: oklch(0.66 0.006 90);
  --accent: oklch(0.26 0.012 90);
  --accent-foreground: oklch(0.96 0 0);
  --destructive: oklch(0.6 0.21 25);
  --destructive-foreground: oklch(0.99 0 0);
  --success: oklch(0.72 0.17 162);
  --warning: oklch(0.78 0.15 70);
  --border: oklch(0.26 0.005 90);
  --input: oklch(0.28 0.005 90);
  --ring: oklch(0.83 0.16 90);
  --radius: 0.625rem;
}

@theme inline {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

@layer base {
  * {
    border-color: var(--color-border);
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
    background-image: radial-gradient(
      1100px 480px at 75% -10%,
      oklch(0.83 0.16 90 / 0.055),
      transparent 60%
    );
    background-attachment: fixed;
  }
  ::selection {
    background: oklch(0.83 0.16 90 / 0.35);
  }
}
```

- [ ] **Step 6: Create `frontend/src/vite-env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 7: Create `frontend/src/types.ts`**

```typescript
export type UserRole = "admin" | "operador";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
```

- [ ] **Step 8: Create `frontend/src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 9: Create `frontend/src/lib/api.ts`**

```typescript
import type { TokenPair } from "@/types";

const BASE = "/api/v1";
const ACCESS_KEY = "gsb_estoque_access";
const REFRESH_KEY = "gsb_estoque_refresh";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}
export function setTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Single-flight: múltiplos 401 simultâneos disparam um único refresh.
let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  refreshPromise ??= (async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) return false;
    try {
      const resp = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resp.ok) return false;
      setTokens((await resp.json()) as TokenPair);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => {
        refreshPromise = null;
      }, 0);
    }
  })();
  return refreshPromise;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

async function rawRequest(path: string, options: RequestOptions): Promise<Response> {
  const url = new URL(BASE + path, window.location.origin);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.json !== undefined) headers["Content-Type"] = "application/json";
  return fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
  });
}

export async function api<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  let resp = await rawRequest(path, options);
  if (resp.status === 401 && !path.startsWith("/auth/")) {
    if (await tryRefresh()) {
      resp = await rawRequest(path, options);
    } else {
      clearTokens();
      window.location.assign("/login");
      throw new ApiError(401, "Sessão expirada");
    }
  }
  if (!resp.ok) {
    let detail = `Erro ${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join("; ");
      }
    } catch {
      /* corpo não-JSON */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
```

- [ ] **Step 10: Create `frontend/src/context/auth.tsx`**

```typescript
import { api, clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/api";
import type { TokenPair, User } from "@/types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface AuthContextValue {
  user: User | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => Boolean(getAccessToken()));

  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/auth/me"),
    enabled: hasToken,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api<TokenPair>("/auth/login", {
        method: "POST",
        json: { email, password },
      });
      setTokens(tokens);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      void api("/auth/logout", { method: "POST", json: { refresh_token: refreshToken } }).catch(
        () => undefined,
      );
    }
    clearTokens();
    setHasToken(false);
    queryClient.clear();
    window.location.assign("/login");
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: hasToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return ctx;
}
```

- [ ] **Step 11: Create `frontend/src/main.tsx`** (wires providers; App comes in Task 8)

```typescript
import { AuthProvider } from "@/context/auth";
import "@/index.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { Toaster } from "sonner";
import App from "@/App";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster theme="dark" position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 12: Install deps**

Run: `cd frontend && npm install`
Expected: dependencies install without errors (`node_modules/` created).

- [ ] **Step 13: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src
git commit -m "feat(frontend): vite/tailwind skeleton with theme, api client and auth context"
```

---

### Task 8: UI primitives, login page, protected shell, routing

**Files:**
- Create: `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/input.tsx`, `frontend/src/components/ui/card.tsx`, `frontend/src/components/ui/label.tsx`
- Create: `frontend/src/components/layout/app-shell.tsx`
- Create: `frontend/src/pages/login.tsx`, `frontend/src/pages/dashboard.tsx`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useAuth` (Task 7), `cn` (Task 7), `api`/`ApiError` (Task 7).
- Produces: `<App/>` route tree with `/login` (public) and protected `/` (shell + dashboard placeholder).

- [ ] **Step 1: Create `frontend/src/components/ui/button.tsx`**

```typescript
import { cn } from "@/lib/utils";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3",
        lg: "h-11 px-6",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";
```

- [ ] **Step 2: Create `frontend/src/components/ui/input.tsx`**

```typescript
import { cn } from "@/lib/utils";
import { forwardRef, type InputHTMLAttributes } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
```

- [ ] **Step 3: Create `frontend/src/components/ui/label.tsx`**

```typescript
import { cn } from "@/lib/utils";
import * as LabelPrimitive from "@radix-ui/react-label";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from "react";

export const Label = forwardRef<
  ElementRef<typeof LabelPrimitive.Root>,
  ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn("text-sm font-medium leading-none", className)}
    {...props}
  />
));
Label.displayName = "Label";
```

- [ ] **Step 4: Create `frontend/src/components/ui/card.tsx`**

```typescript
import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-xl border border-border bg-card text-card-foreground shadow", className)}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-6", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-lg font-semibold tracking-tight", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6 pt-0", className)} {...props} />;
}
```

- [ ] **Step 5: Create `frontend/src/pages/login.tsx`**

```typescript
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/auth";
import { ApiError } from "@/lib/api";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao entrar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>GrupoSB Estoque</CardTitle>
          <p className="text-sm text-muted-foreground">Entre para acessar o sistema</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/layout/app-shell.tsx`**

```typescript
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth";
import { Boxes, LayoutDashboard, LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/itens", label: "Itens", icon: Boxes, end: false },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 flex-col border-r border-border bg-card p-4 md:flex">
        <div className="mb-6 px-2 text-lg font-bold tracking-tight">
          GrupoSB <span className="text-primary">Estoque</span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center justify-between px-2 pt-4">
          <span className="truncate text-xs text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="icon" onClick={logout} title="Sair">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 7: Create `frontend/src/pages/dashboard.tsx`** (placeholder; real KPIs land in the reports phase)

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/auth";

export default function DashboardPage() {
  const { user } = useAuth();
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Bem-vindo, {user?.full_name || user?.email}.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Fundação pronta</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Login e estrutura no ar. Os módulos de peças, máquinas e relatórios entram nas
          próximas fases.
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 8: Create `frontend/src/App.tsx`** (routing + guards)

```typescript
import AppShell from "@/components/layout/app-shell";
import { useAuth } from "@/context/auth";
import DashboardPage from "@/pages/dashboard";
import LoginPage from "@/pages/login";
import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router";

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div className="p-6 text-muted-foreground">Carregando...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route path="/" element={<DashboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 9: Type-check and build**

Run: `cd frontend && npm run build`
Expected: `tsc -b` passes with no errors and Vite produces `dist/`.

- [ ] **Step 10: Manual smoke test (login end-to-end)**

Start the backend seeded (from Task 6): `cd backend && .venv/Scripts/python -m scripts.seed` then `cd backend && .venv/Scripts/python run.py`.
In another terminal: `cd frontend && npm run dev`. Open `http://localhost:5173`, log in with `admin@gruposb.com` / `admin123`.
Expected: redirect to the dashboard showing the admin email; reload keeps the session; the Sair button returns to `/login`.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/components frontend/src/pages frontend/src/App.tsx
git commit -m "feat(frontend): ui primitives, login page and protected app shell"
```

---

### Task 9: Ops — docker-compose, single-origin serve script, project docs

**Files:**
- Create: `docker-compose.yml`, `serve-lan.ps1`
- Create: `README.md`, `CLAUDE.md`, `HANDOFF.md`

**Interfaces:**
- Consumes: backend (`run.py`, `.env`), frontend (`npm run build`, `frontend/dist`).
- Produces: LAN single-origin serving and dev infra; onboarding docs.

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
name: gruposb-estoque

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: estoque
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-estoque}
      POSTGRES_DB: estoque
    ports:
      # 5433 no host: a máquina de dev tem PostgreSQL nativo em 5432.
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U estoque -d estoque"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build: ./backend
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    environment:
      DATABASE_URL: postgresql+psycopg://estoque:${POSTGRES_PASSWORD:-estoque}@db:5432/estoque
      AUTO_CREATE_TABLES: "false"
      SECRET_KEY: ${SECRET_KEY:-dev-secret-troque-em-producao-0000000000}
      CORS_ORIGINS: http://localhost:5173,http://127.0.0.1:5173
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy

  frontend:
    image: node:24-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    environment:
      VITE_PROXY_TARGET: http://api:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    depends_on:
      - api

volumes:
  pgdata:
```

> Note: `build: ./backend` expects a `backend/Dockerfile`. Add one when containerizing the API; for local dev the compose `db` service is enough (run the API with `python run.py`). Creating the Dockerfile is deferred to the deploy phase.

- [ ] **Step 2: Create `serve-lan.ps1`**

```powershell
# Builda o frontend e sobe a API servindo a SPA (origem única) na rede local.
# Uso: .\serve-lan.ps1
$ErrorActionPreference = "Stop"

Push-Location frontend
npm install
npm run build
Pop-Location

Push-Location backend
$env:FRONTEND_DIST = "../frontend/dist"
$env:API_HOST = "0.0.0.0"
Write-Host "Servindo em http://<ip-da-maquina>:8000 (origem única)"
.\.venv\Scripts\python run.py
Pop-Location
```

> Antes de expor na rede (PowerShell como admin, uma vez):
> `New-NetFirewallRule -DisplayName "GrupoSB Estoque" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private`

- [ ] **Step 3: Create `README.md`**

```markdown
# GrupoSB Estoque

Gerenciador de estoque (peças + máquinas) do Grupo SB. Migração do sistema em Google Apps
Script para uma aplicação web independente, espelhando a arquitetura do `gsb-crm`.

**Stack:** FastAPI + SQLAlchemy async (Python) · React 19 + TS + Vite + Tailwind 4 · PostgreSQL 16 (ou SQLite em dev).

## Rodar em dev (SQLite, zero infra)

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows
pip install -e ".[dev]"
python -m scripts.seed            # admin@gruposb.com / admin123
python run.py                     # http://127.0.0.1:8000 (docs: /api/v1/docs)

# Frontend (outro terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

## Testes

```bash
cd backend && .venv/Scripts/python -m pytest
cd frontend && npm run build      # type-check + build
```

## Rede local (origem única)

`.\serve-lan.ps1` builda o front e sobe a API servindo a SPA em `http://<ip>:8000`.

Consulte `docs/superpowers/specs/` para o design e `docs/superpowers/plans/` para os planos por fase.
```

- [ ] **Step 4: Create `CLAUDE.md`**

```markdown
# GrupoSB Estoque — memória do projeto

Gerenciador de estoque do Grupo SB (peças + máquinas), migrado do Google Apps Script.
Dono: Arthur (gruposb.dev@gmail.com). Idioma do produto: pt-BR. Commits: inglês, conventional.

## Stack
- Backend `backend/`: FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, PyJWT (access 15min +
  refresh 7d rotacionado), pwdlib/Argon2id. Postgres 16 (compose, porta 5433) ou SQLite fallback.
- Frontend `frontend/`: React 19, TS estrito, Vite 6, Tailwind 4 (tokens em `src/index.css`),
  UI shadcn-style à mão em `components/ui/`, TanStack Query 5, react-router 7.
- Tema escuro único preto/cinza + amarelo `oklch(0.83 0.16 90)`; verde/vermelho só semânticos.

## Domínio (preservar do sistema antigo)
- Estoque **event-sourced**: `movements` é ledger append-only; saldo é derivado (`saldo_cache`
  é cache recomputável). Tipos: ENTRADA/SAIDA/AJUSTE_POS/AJUSTE_NEG.
- Dois módulos: peças (`items` + ledger) e máquinas (`machine_models` → `machine_units`).
- Papéis: `admin` | `operador`.

## Convenções e armadilhas
- Modelos herdam `TableBase` (UUID pk + created/updated). Enums: StrEnum + `native_enum=False`.
- Windows: psycopg async exige SelectorEventLoop → `app/core/aio.py` + `python run.py`
  (não `uvicorn app.main:app` com Postgres). Hot-reload só no modo SQLite.
- Migrações autogeradas contra SQLite scratch; revisar `server_default` em colunas NOT NULL novas.
- Datas: schemas Out usam `UTCDateTime` (`schemas/common.py`) — SQLite devolve naive.
- Origem única: `FRONTEND_DIST` faz a API servir a SPA (sem CORS). `serve-lan.ps1` na raiz.
- Frontend: paginação `Page<T>`; `lib/api.ts` faz refresh single-flight e redirect p/ /login em 401.

## Receita p/ novo módulo
model → schemas → router (padrão `users.py`/`auth.py`) → `api/router.py` → migração → teste →
`types.ts` → página → rota em `App.tsx` → item no `NAV` do `app-shell.tsx`.

## Comandos
```
backend: python -m scripts.seed        # admin@gruposb.com / admin123
backend: python run.py                 # API dev
backend: python -m pytest              # testes
frontend: npm run dev | npm run build
```

## Estado
Fundação (scaffold + auth) implementada. Próximas fases: núcleo de peças (ledger), máquinas,
relatórios/dashboard, ETL da planilha. Ver `docs/superpowers/plans/`.
```

- [ ] **Step 5: Create `HANDOFF.md`**

```markdown
# HANDOFF — GrupoSB Estoque

## Última sessão
Fundação implementada a partir do plano `docs/superpowers/plans/2026-08-07-foundation-scaffold-auth.md`:
- Backend FastAPI: config, async DB (Postgres/SQLite), `TableBase`, security (Argon2+JWT),
  auth (login/refresh/logout/me/bootstrap) com rate-limit, users CRUD (admin), seed, migração baseline.
- Frontend React/Vite/Tailwind 4: tema, api client com refresh, auth context, login, app-shell,
  dashboard placeholder, rotas protegidas.
- Testes backend passando (security, auth, users). `npm run build` limpo.

## Como validar
`cd backend && python -m pytest` · `cd frontend && npm run build` · login manual admin/admin123.

## Próximos passos (nova fase, novo plano)
1. **Núcleo de peças**: `Category`, `Item`, `Movement` (ledger), serviço de movimentação com saldo
   derivado + trava por transação (`SELECT ... FOR UPDATE`), ajuste, histórico. (spec §4–§5)
2. **Máquinas**: `MachineModel` + `MachineUnit`.
3. **Relatórios + alertas + dashboard** (Recharts).
4. **ETL**: `scripts/import_sheets.py` — importar o export `.xlsx` da planilha e conferir saldos.

## Pendências conhecidas
- `backend/Dockerfile` ainda não criado (compose `api` depende dele) — fazer na fase de deploy.
- HTTPS não terminado pela API — em rede local usar Cloudflare Tunnel/Tailscale.
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml serve-lan.ps1 README.md CLAUDE.md HANDOFF.md
git commit -m "docs: dev infra, single-origin serve script and project docs"
```

---

## Self-Review

**1. Spec coverage (foundation slice of spec §3, §4-users, §5-auth, §6-frontend, §8, §10 phases 0-1):**
- Project structure (spec §3) → Tasks 1, 7, 9. ✓
- `users`/`refresh_tokens` model + UUID `TableBase` + StrEnum (spec §4) → Task 3. ✓
- Auth endpoints + roles + rate-limit + refuse-boot guard (spec §5, §8) → Tasks 1 (guard), 4. ✓
- Users admin CRUD (spec §5) → Task 5. ✓
- Frontend theme/kit/api client/auth (spec §6) → Tasks 7, 8. ✓
- Single-origin serve, Windows loop, SQLite fallback (spec §3, §8) → Tasks 1, 9. ✓
- Tests with in-memory SQLite (spec §9) → Tasks 2, 4, 5. ✓
- Seed + Alembic baseline (spec §10 phase 0-1) → Task 6. ✓
- Domain models (items/movements/machines), reports, ETL → **out of scope for this plan** (spec §10 phases 2-5, each gets its own plan). Noted in HANDOFF.

**2. Placeholder scan:** No "TBD"/"add validation"/"similar to". The dashboard is an intentional placeholder page (labeled), not a plan placeholder. The `backend/Dockerfile` gap is explicitly flagged, not silently assumed.

**3. Type consistency:** `create_token_pair` dict keys used identically in Task 2 and Task 4. `UserRole` values `admin`/`operador` consistent across models (Task 3), tests (Tasks 4-5), and frontend `types.ts` (Task 7). `Page[T]` (backend Task 3) mirrors `Page<T>` (frontend Task 7). `api<T>()` signature in Task 7 matches usage in Tasks 7-8. `require_roles`/`get_current_user`/`DbSession` defined in Task 3, consumed in Tasks 4-5.
