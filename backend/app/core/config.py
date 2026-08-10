from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GrupoSB Estoque"
    env: str = "dev"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Caminho do build do frontend (frontend/dist). Preenchido = API serve a SPA
    # na raiz (origem única, sem CORS). Vazio = API pura (dev com Vite).
    frontend_dist: str = ""

    # --- Supabase ---
    supabase_url: str = ""  # ex.: https://xxxx.supabase.co
    # JWT secret do projeto (Project Settings → API). Valida os tokens do Supabase Auth.
    supabase_jwt_secret: str = "dev-supabase-jwt-secret-troque-000000000000"
    # Service role key — SÓ no backend (cria usuários via Admin API). Nunca no front.
    supabase_service_role_key: str = ""

    # Dev: SQLite local, zero infra. Produção: session pooler do Supabase
    # (postgresql+psycopg://postgres.<ref>:<senha>@aws-...pooler.supabase.com:5432/postgres).
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
