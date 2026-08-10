import uuid

import pytest

from app.models import Item, Movement, MovementType, Technician
from app.services.inventory_service import (
    adjust_balance,
    register_movement,
    status_do_saldo,
)
from tests.helpers import auth_headers


def test_status_thresholds():
    assert status_do_saldo(0, 5) == "Em falta"
    assert status_do_saldo(3, 5) == "Ruim"
    assert status_do_saldo(7, 5) == "Alerta"
    assert status_do_saldo(20, 5) == "Bom"
    assert status_do_saldo(1, 0) == "Bom"
    assert status_do_saldo(5, 5) == "Alerta"   # saldo == minimo
    assert status_do_saldo(4, 5) == "Ruim"     # saldo == minimo - 1
    assert status_do_saldo(10, 5) == "Bom"     # saldo == 2*minimo
    assert status_do_saldo(9, 5) == "Alerta"   # saldo == 2*minimo - 1


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
