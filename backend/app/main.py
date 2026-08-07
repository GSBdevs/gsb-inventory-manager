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
    if settings.env != "dev" and "dev-supabase-jwt-secret" in settings.supabase_jwt_secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET de desenvolvimento com ENV != dev. "
            "Use o JWT secret real do projeto Supabase (Project Settings → API)."
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
