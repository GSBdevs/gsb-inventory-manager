import uuid

import pytest

from app.core.supabase import get_supabase_admin
from app.main import app
from tests.helpers import auth_headers

ADMIN_SUB = "11111111-1111-1111-1111-111111111111"
OP_SUB = "22222222-2222-2222-2222-222222222222"


class _FakeAdmin:
    async def create_user(self, email: str, password: str) -> str:
        return str(uuid.uuid4())


@pytest.fixture
def admin_client(client):
    app.dependency_overrides[get_supabase_admin] = lambda: _FakeAdmin()
    return client


async def _become_admin(admin_client):
    # 1º usuário autenticado é provisionado como admin (bootstrap).
    await admin_client.get(
        "/api/v1/auth/me", headers=auth_headers(sub=ADMIN_SUB, email="admin@gruposb.com")
    )


async def test_admin_creates_and_lists_users(admin_client):
    await _become_admin(admin_client)
    created = await admin_client.post(
        "/api/v1/users",
        headers=auth_headers(sub=ADMIN_SUB),
        json={"email": "op@gruposb.com", "password": "op12345", "role": "operador"},
    )
    assert created.status_code == 201
    assert created.json()["role"] == "operador"

    listing = await admin_client.get("/api/v1/users", headers=auth_headers(sub=ADMIN_SUB))
    assert listing.status_code == 200
    assert listing.json()["total"] == 2  # admin + operador


async def test_operador_cannot_manage_users(admin_client):
    await _become_admin(admin_client)
    # Provisiona um operador (2º usuário) e usa o token dele.
    await admin_client.get(
        "/api/v1/auth/me", headers=auth_headers(sub=OP_SUB, email="op2@gruposb.com")
    )
    resp = await admin_client.get("/api/v1/users", headers=auth_headers(sub=OP_SUB))
    assert resp.status_code == 403


async def test_create_rejects_duplicate_email(admin_client):
    await _become_admin(admin_client)
    payload = {"email": "dup@gruposb.com", "password": "dup12345"}
    first = await admin_client.post(
        "/api/v1/users", headers=auth_headers(sub=ADMIN_SUB), json=payload
    )
    assert first.status_code == 201
    second = await admin_client.post(
        "/api/v1/users", headers=auth_headers(sub=ADMIN_SUB), json=payload
    )
    assert second.status_code == 409


async def test_admin_updates_user(admin_client):
    await _become_admin(admin_client)
    created = await admin_client.post(
        "/api/v1/users",
        headers=auth_headers(sub=ADMIN_SUB),
        json={"email": "op@gruposb.com", "password": "op12345"},
    )
    user_id = created.json()["id"]
    resp = await admin_client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers(sub=ADMIN_SUB),
        json={"role": "admin", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
    assert resp.json()["is_active"] is False
