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
