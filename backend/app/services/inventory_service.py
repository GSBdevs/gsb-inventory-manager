import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item, Movement, MovementType, Technician
from app.models.movement import SINAL

QTD_MAX = 1_000_000


def _norm(text) -> str:
    return " ".join(str(text or "").split()).strip()


def status_do_saldo(saldo: int, minimo: int) -> str:
    saldo = int(saldo or 0)
    minimo = int(minimo or 0)
    if saldo <= 0:
        return "Em falta"
    if minimo > 0 and saldo < minimo:
        return "Ruim"
    if minimo > 0 and saldo < minimo * 2:
        return "Alerta"
    return "Bom"


def _validar_qtd(valor, contexto: str, permitir_zero: bool = False) -> int:
    try:
        q = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Quantidade inválida ({contexto}).") from None
    if q != float(valor):
        raise ValueError(f"A quantidade deve ser inteira ({contexto}).")
    if q < (0 if permitir_zero else 1):
        raise ValueError(f"Quantidade fora do permitido ({contexto}).")
    if q > QTD_MAX:
        raise ValueError("Quantidade acima do limite.")
    return q


async def register_movement(
    db: AsyncSession, tipo: MovementType, batch: dict, operador: str
) -> dict:
    if tipo not in (MovementType.ENTRADA, MovementType.SAIDA):
        raise ValueError("Tipo de movimentação inválido.")
    linhas = batch.get("itens") or []
    if not linhas:
        raise ValueError("Adicione pelo menos uma peça.")

    tecnico_id = batch.get("tecnico_id")
    if tecnico_id is not None:
        tecnico = await db.get(Technician, tecnico_id)
        if tecnico is None:
            raise ValueError("Selecione um técnico válido.")
    else:
        raise ValueError("Selecione um técnico.")

    referencia = _norm(batch.get("referencia"))
    sinal = SINAL[tipo]

    saldo_final: dict[uuid.UUID, int] = {}
    nome_do_item: dict[uuid.UUID, str] = {}
    novos = 0
    movimentos: list[Movement] = []

    for linha in linhas:
        q = _validar_qtd(linha.get("quantidade"), _norm(linha.get("peca")) or "item")
        item: Item | None = None

        if tipo == MovementType.ENTRADA and linha.get("novo"):
            nome = _norm(linha.get("peca"))
            if not nome:
                raise ValueError("Informe o nome da nova peça.")
            existe = await db.scalar(select(Item).where(func.lower(Item.nome) == nome.lower()))
            if existe is not None:
                raise ValueError(f'A peça "{nome}" já existe. Desmarque "Item novo".')
            item = Item(
                nome=nome,
                category_id=linha.get("categoria_id"),
                unidade=_norm(linha.get("unidade")) or "un",
                estoque_minimo=int(linha.get("estoque_minimo") or 0),
                observacoes=_norm(linha.get("observacoes")),
                saldo_cache=0,
            )
            db.add(item)
            await db.flush()  # garante item.id
            novos += 1
        else:
            item_id = linha.get("item_id")
            if item_id is None:
                nome = _norm(linha.get("peca"))
                item = await db.scalar(select(Item).where(func.lower(Item.nome) == nome.lower()))
            else:
                item = await db.scalar(
                    select(Item).where(Item.id == item_id).with_for_update()
                )
            if item is None:
                referencia_item = linha.get("peca") or linha.get("item_id")
                raise ValueError(f'Peça não encontrada no estoque: "{referencia_item}".')

        atual = saldo_final.get(item.id, int(item.saldo_cache or 0))
        if tipo == MovementType.SAIDA and q > atual:
            raise ValueError(
                f'Quantidade insuficiente para "{item.nome}" '
                f"(disponível: {atual}, solicitado: {q})."
            )
        novo_saldo = atual + sinal * q
        saldo_final[item.id] = novo_saldo
        nome_do_item[item.id] = item.nome

        movimentos.append(
            Movement(
                tipo=tipo,
                item_id=item.id,
                quantidade=q,
                tecnico_id=tecnico_id,
                referencia=referencia,
                detalhes=_norm(linha.get("detalhes")),
                registrado_por=operador,
                saldo_resultante=novo_saldo,
            )
        )

    for mov in movimentos:
        db.add(mov)
    for item_id, saldo in saldo_final.items():
        item = await db.get(Item, item_id)
        item.saldo_cache = saldo

    await db.commit()
    return {
        "registros": len(movimentos),
        "novas_pecas": novos,
        "saldos": [
            {"item_id": iid, "nome": nome_do_item[iid], "saldo": s}
            for iid, s in saldo_final.items()
        ],
    }


async def adjust_balance(
    db: AsyncSession, item_id: uuid.UUID, novo_saldo: int, motivo: str, operador: str
) -> dict:
    item = await db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if item is None:
        raise ValueError("Item não encontrado.")
    alvo = _validar_qtd(novo_saldo, item.nome, permitir_zero=True)
    atual = int(item.saldo_cache or 0)
    delta = alvo - atual
    if delta == 0:
        return {"alterado": False, "saldo": atual, "message": "Saldo já estava correto."}
    tipo = MovementType.AJUSTE_POS if delta > 0 else MovementType.AJUSTE_NEG
    db.add(
        Movement(
            tipo=tipo,
            item_id=item.id,
            quantidade=abs(delta),
            tecnico_id=None,
            referencia=_norm(motivo) or "ajuste de saldo",
            registrado_por=operador,
            saldo_resultante=alvo,
        )
    )
    item.saldo_cache = alvo
    await db.commit()
    return {
        "alterado": True,
        "saldo_anterior": atual,
        "saldo": alvo,
        "delta": delta,
        "tipo": tipo,
    }
