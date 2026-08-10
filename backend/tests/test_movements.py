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
