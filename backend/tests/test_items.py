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
    await client.post(
        "/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "Cilindro OPC"}
    )
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


async def test_status_reflects_stock(client):
    created = await client.post(
        "/api/v1/items",
        headers=auth_headers(sub=USER),
        json={"nome": "Toner", "estoque_minimo": 5},
    )
    assert created.json()["status"] == "Em falta"  # saldo inicial 0


async def test_rename_to_own_name_variant_succeeds(client):
    created = await client.post(
        "/api/v1/items", headers=auth_headers(sub=USER), json={"nome": "Belt"}
    )
    item_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/items/{item_id}",
        headers=auth_headers(sub=USER),
        json={"nome": "  belt "},
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "belt"
