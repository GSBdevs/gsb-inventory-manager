import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAdjustItem } from "@/lib/queries";
import type { Item } from "@/types";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

export function AdjustDialog({ item, onClose }: { item: Item | null; onClose: () => void }) {
  const adjust = useAdjustItem();
  const [novoSaldo, setNovoSaldo] = useState(0);
  const [motivo, setMotivo] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!item) return;
    try {
      await adjust.mutateAsync({ id: item.id, novo_saldo: novoSaldo, motivo });
      toast.success(`Saldo de "${item.nome}" ajustado para ${novoSaldo}.`);
      onClose();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao ajustar saldo");
    }
  }

  return (
    <Dialog open={item !== null} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogTitle>Ajustar saldo{item ? ` — ${item.nome}` : ""}</DialogTitle>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Saldo atual: <span className="text-foreground">{item?.saldo ?? 0}</span>. O ajuste gera
            um lançamento no histórico (não apaga nada).
          </p>
          <div className="flex flex-col gap-2">
            <Label htmlFor="novo">Novo saldo</Label>
            <Input
              id="novo"
              type="number"
              min={0}
              value={novoSaldo}
              onChange={(e) => setNovoSaldo(Number(e.target.value))}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="motivo">Motivo</Label>
            <Input id="motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </div>
          <Button type="submit" disabled={adjust.isPending}>
            {adjust.isPending ? "Ajustando..." : "Confirmar ajuste"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
