import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { useCreateMovement, useCreateTechnician, useItems, useTechnicians } from "@/lib/queries";
import type { MovementLineInput, MovementType } from "@/types";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface Linha {
  item_id: string;
  novo: boolean;
  peca: string;
  quantidade: number;
  detalhes: string;
}

function linhaVazia(): Linha {
  return { item_id: "", novo: false, peca: "", quantidade: 1, detalhes: "" };
}

export default function MovimentarPage() {
  const { data: itensPage } = useItems("");
  const { data: tecnicos } = useTechnicians();
  const criar = useCreateMovement();
  const criarTec = useCreateTechnician();

  const [tipo, setTipo] = useState<MovementType>("ENTRADA");
  const [tecnicoId, setTecnicoId] = useState("");
  const [novoTec, setNovoTec] = useState(false);
  const [novoTecNome, setNovoTecNome] = useState("");
  const [referencia, setReferencia] = useState("");
  const [linhas, setLinhas] = useState<Linha[]>([linhaVazia()]);

  const itens = itensPage?.items ?? [];

  function atualizar(i: number, patch: Partial<Linha>) {
    setLinhas((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  async function criarTecnico() {
    const nome = novoTecNome.trim();
    if (!nome) return;
    try {
      const t = await criarTec.mutateAsync(nome);
      setTecnicoId(t.id);
      setNovoTec(false);
      setNovoTecNome("");
      toast.success(`Técnico "${t.nome}" criado.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao criar técnico");
    }
  }

  async function onSubmit() {
    if (!tecnicoId) {
      toast.error("Selecione um técnico.");
      return;
    }
    const payloadItens: MovementLineInput[] = linhas.map((l) =>
      l.novo
        ? { novo: true, peca: l.peca, quantidade: l.quantidade, detalhes: l.detalhes }
        : { item_id: l.item_id, quantidade: l.quantidade, detalhes: l.detalhes },
    );
    try {
      const res = await criar.mutateAsync({
        tipo,
        referencia,
        tecnico_id: tecnicoId,
        itens: payloadItens,
      });
      toast.success(
        `${res.registros} lançamento(s). ` +
          res.saldos.map((s) => `${s.nome}: ${s.saldo}`).join(" · "),
      );
      setLinhas([linhaVazia()]);
      setReferencia("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao registrar movimentação");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Movimentar</h1>
        <p className="text-sm text-muted-foreground">Registre entradas e saídas de peças.</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="flex flex-col gap-2">
          <Label>Tipo</Label>
          <Select value={tipo} onChange={(e) => setTipo(e.target.value as MovementType)}>
            <option value="ENTRADA">Entrada</option>
            <option value="SAIDA">Saída</option>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label>Técnico</Label>
          <Select value={tecnicoId} onChange={(e) => setTecnicoId(e.target.value)}>
            <option value="">Selecione...</option>
            {(tecnicos ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </Select>
          {novoTec ? (
            <div className="flex gap-2">
              <Input
                placeholder="Nome do técnico"
                value={novoTecNome}
                onChange={(e) => setNovoTecNome(e.target.value)}
              />
              <Button type="button" size="sm" onClick={criarTecnico} disabled={criarTec.isPending}>
                Criar
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setNovoTec(false)}>
                Cancelar
              </Button>
            </div>
          ) : (
            <button
              type="button"
              className="text-left text-xs text-primary hover:underline"
              onClick={() => setNovoTec(true)}
            >
              + Novo técnico
            </button>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label>Referência</Label>
          <Input value={referencia} onChange={(e) => setReferencia(e.target.value)} placeholder="NF, OS..." />
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {linhas.map((l, i) => (
          <Card key={i}>
            <CardContent className="flex flex-wrap items-end gap-3 p-4">
              <div className="flex min-w-[220px] flex-1 flex-col gap-2">
                <Label>Peça</Label>
                {tipo === "ENTRADA" && l.novo ? (
                  <Input
                    placeholder="Nome da nova peça"
                    value={l.peca}
                    onChange={(e) => atualizar(i, { peca: e.target.value })}
                  />
                ) : (
                  <Select value={l.item_id} onChange={(e) => atualizar(i, { item_id: e.target.value })}>
                    <option value="">Selecione...</option>
                    {itens.map((it) => (
                      <option key={it.id} value={it.id}>
                        {it.nome} (saldo {it.saldo})
                      </option>
                    ))}
                  </Select>
                )}
              </div>
              <div className="flex w-28 flex-col gap-2">
                <Label>Qtd</Label>
                <Input
                  type="number"
                  min={1}
                  value={l.quantidade}
                  onChange={(e) => atualizar(i, { quantidade: Number(e.target.value) })}
                />
              </div>
              {tipo === "ENTRADA" && (
                <label className="flex items-center gap-2 pb-2.5 text-sm text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={l.novo}
                    onChange={(e) => atualizar(i, { novo: e.target.checked, item_id: "", peca: "" })}
                  />
                  Item novo
                </label>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLinhas((ls) => (ls.length > 1 ? ls.filter((_, idx) => idx !== i) : ls))}
                title="Remover linha"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button variant="secondary" onClick={() => setLinhas((ls) => [...ls, linhaVazia()])}>
          <Plus className="h-4 w-4" /> Adicionar peça
        </Button>
        <Button onClick={onSubmit} disabled={criar.isPending}>
          {criar.isPending ? "Registrando..." : `Registrar ${tipo === "ENTRADA" ? "entrada" : "saída"}`}
        </Button>
      </div>
    </div>
  );
}
