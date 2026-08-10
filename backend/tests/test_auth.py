from tests.helpers import auth_headers, make_token


async def test_me_provisions_first_user_as_admin(client):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(email="admin@gruposb.com"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "admin@gruposb.com"
    assert body["role"] == "admin"


async def test_second_user_is_operador(client):
    await client.get("/api/v1/auth/me", headers=auth_headers(email="admin@gruposb.com"))
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(email="op@gruposb.com"))
    assert resp.status_code == 200
    assert resp.json()["role"] == "operador"


async def test_me_without_token_is_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_with_bad_secret_is_401(client):
    token = make_token(secret="outro-secret-invalido-000000000000")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_with_wrong_audience_is_401(client):
    token = make_token(aud="anon")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
