import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class SupabaseAdmin:
    """Cliente da Admin API do Supabase Auth (usa a service role key).

    Injetável via `get_supabase_admin` para ser substituído nos testes.
    """

    async def create_user(self, email: str, password: str) -> str:
        """Cria um usuário no Supabase Auth e devolve o id (uuid) criado."""
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Supabase Admin não configurado (defina SUPABASE_URL e SERVICE_ROLE_KEY)",
            )
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.supabase_url}/auth/v1/admin/users",
                headers=headers,
                json={"email": email, "password": password, "email_confirm": True},
            )
        if resp.status_code >= 400:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Supabase Admin: {resp.text}")
        return resp.json()["id"]


def get_supabase_admin() -> SupabaseAdmin:
    return SupabaseAdmin()
