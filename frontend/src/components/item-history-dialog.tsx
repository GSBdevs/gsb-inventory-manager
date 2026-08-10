import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Table, Td, Th } from "@/components/ui/table";
import { useItemHistory } from "@/lib/queries";
import type { Item } from "@/types";

const TIPO_LABEL: Record<string, string> = {
  ENTRADA: "Entrada",
  SAIDA: "Saída",
  AJUSTE_POS: "Ajuste +",
  AJUSTE_NEG: "Ajuste −",
};

export function ItemHistoryDialog({ item, onClose }: { item: Item | null; onClose: () => void }) {
  const { data, isLoading } = useItemHistory(item?.id ?? null);

  return (
    <Dialog open={item !== null} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogTitle>Histórico{item ? ` — ${item.nome}` : ""}</DialogTitle>
        {isLoading ? (
          <p className="text-muted-foreground">Carregando...</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Data</Th>
                <Th>Tipo</Th>
                <Th className="text-right">Qtd</Th>
                <Th>Técnico</Th>
                <Th className="text-right">Saldo</Th>
              </tr>
            </thead>
            <tbody>
              {(data?.movimentacoes ?? []).map((m) => (
                <tr key={m.id}>
                  <Td className="text-muted-foreground">
                    {new Date(m.data).toLocaleDateString("pt-BR")}
                  </Td>
                  <Td>{TIPO_LABEL[m.tipo] ?? m.tipo}</Td>
                  <Td className="text-right">
                    {m.sinal > 0 ? "+" : "−"}
                    {m.quantidade}
                  </Td>
                  <Td className="text-muted-foreground">{m.tecnico || "—"}</Td>
                  <Td className="text-right">{m.saldo_resultante}</Td>
                </tr>
              ))}
              {data && data.movimentacoes.length === 0 && (
                <tr>
                  <Td colSpan={5} className="text-center text-muted-foreground">
                    Sem movimentações.
                  </Td>
                </tr>
              )}
            </tbody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}
