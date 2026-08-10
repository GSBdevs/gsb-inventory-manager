import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateItem } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

export function ItemFormDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const create = useCreateItem();
  const [nome, setNome] = useState("");
  const [unidade, setUnidade] = useState("un");
  const [minimo, setMinimo] = useState(0);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await create.mutateAsync({ nome, unidade, estoque_minimo: minimo });
      toast.success(`Peça "${nome}" criada.`);
      setNome("");
      setUnidade("un");
      setMinimo(0);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Falha ao criar peça");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>Nova peça</DialogTitle>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="nome">Nome</Label>
            <Input id="nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor="unidade">Unidade</Label>
              <Input id="unidade" value={unidade} onChange={(e) => setUnidade(e.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="minimo">Estoque mínimo</Label>
              <Input
                id="minimo"
                type="number"
                min={0}
                value={minimo}
                onChange={(e) => setMinimo(Number(e.target.value))}
              />
            </div>
          </div>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Salvando..." : "Criar peça"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
