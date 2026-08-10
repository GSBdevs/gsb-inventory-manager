import { AdjustDialog } from "@/components/adjust-dialog";
import { ItemFormDialog } from "@/components/item-form-dialog";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, Td, Th } from "@/components/ui/table";
import { useItems } from "@/lib/queries";
import { useDebounce } from "@/hooks/use-debounce";
import type { Item } from "@/types";
import { Plus, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

export default function ItensPage() {
  const [busca, setBusca] = useState("");
  const q = useDebounce(busca, 300);
  const { data, isLoading } = useItems(q);
  const [criar, setCriar] = useState(false);
  const [ajustar, setAjustar] = useState<Item | null>(null);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Itens</h1>
          <p className="text-sm text-muted-foreground">Catálogo de peças e saldo atual.</p>
        </div>
        <Button onClick={() => setCriar(true)}>
          <Plus className="h-4 w-4" /> Nova peça
        </Button>
      </div>

      <Input
        placeholder="Buscar por nome ou SKU..."
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        className="max-w-sm"
      />

      {isLoading ? (
        <p className="text-muted-foreground">Carregando...</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Peça</Th>
              <Th>Unidade</Th>
              <Th className="text-right">Saldo</Th>
              <Th className="text-right">Mínimo</Th>
              <Th>Status</Th>
              <Th className="text-right">Ações</Th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((item) => (
              <tr key={item.id} className="hover:bg-accent/40">
                <Td className="font-medium">{item.nome}</Td>
                <Td className="text-muted-foreground">{item.unidade}</Td>
                <Td className="text-right">{item.saldo}</Td>
                <Td className="text-right text-muted-foreground">{item.estoque_minimo}</Td>
                <Td>
                  <StatusBadge status={item.status} />
                </Td>
                <Td className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => setAjustar(item)}>
                    <SlidersHorizontal className="h-4 w-4" /> Ajustar
                  </Button>
                </Td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <Td colSpan={6} className="text-center text-muted-foreground">
                  Nenhuma peça encontrada.
                </Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}

      <ItemFormDialog open={criar} onOpenChange={setCriar} />
      <AdjustDialog item={ajustar} onClose={() => setAjustar(null)} />
    </div>
  );
}
