# Fase — Frontend de Peças — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parts UI — a catalog page (with derived-balance status pills, search, create, adjust), a movement page (entrada/saída in batch, on-the-fly new item), and a per-item ledger history — consuming the Phase 2 backend API.

**Architecture:** React 19 + Vite + Tailwind 4 on the existing foundation. Data access via TanStack Query hooks in `lib/queries.ts` over the existing `api<T>()` client (Supabase-session bearer). Modals use Radix Dialog; dropdowns use styled **native `<select>`** (avoids the Radix-Select-inside-Dialog pointer bug). Pages wire into the existing `App.tsx` routes and the app-shell `NAV`.

**Tech Stack:** React 19, TS strict, Vite 6, Tailwind 4, TanStack Query 5, react-router 7, @radix-ui/react-dialog, lucide-react, sonner. No test framework in the frontend — each task's gate is a clean `npm run build` (`tsc -b && vite build`); the final task adds a manual browser smoke test.

## Global Constraints

- Product language pt-BR (all UI strings); code identifiers English; commits English conventional.
- TypeScript strict; every task ends with a clean `npm run build`. No `any`, no `@ts-ignore`, no tsconfig weakening to force the build.
- Dark-only theme; use semantic tokens via `cn()` (`bg-card`, `text-muted-foreground`, `border-input`, `bg-primary`, etc.). Status colors: **Bom**→success/green, **Alerta**→warning/yellow, **Ruim**→orange, **Em falta**→destructive/red. Yellow `oklch(0.83 0.16 90)` is the primary accent, never a full background.
- Dropdowns use styled native `<select>` (NOT Radix Select). Modals use Radix Dialog.
- API base is `/api/v1` via the existing `api<T>(path, {method, json, params})`; the token comes from the Supabase session automatically. Never call Supabase or the API directly with a hand-built fetch.
- Types must match the backend exactly (see Task 1). `ItemOut.saldo` is the derived balance; `status` is computed server-side.

---

## File Structure

```
frontend/src/
  types.ts                         # + Item, Category, Technician, Movement*, History*
  lib/queries.ts                   # api fns + TanStack Query hooks (NEW)
  components/ui/
    badge.tsx                      # status pill (NEW)
    dialog.tsx                     # Radix Dialog wrapper (NEW)
    textarea.tsx                   # (NEW)
    select.tsx                     # styled native <select> (NEW)
    table.tsx                      # simple table primitives (NEW)
  components/
    item-form-dialog.tsx           # criar/editar peça (NEW, Task 2)
    adjust-dialog.tsx              # ajustar saldo (NEW, Task 2)
    item-history-dialog.tsx        # histórico do item (NEW, Task 4)
  pages/
    itens.tsx                      # catálogo (NEW, Task 2)
    movimentar.tsx                 # entrada/saída (NEW, Task 3)
  App.tsx                          # + rotas /itens e /movimentar
  components/layout/app-shell.tsx  # + item de NAV "Movimentar"
```

---

### Task 1: Types, data hooks, UI primitives

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/package.json` (add `@radix-ui/react-dialog`)
- Create: `frontend/src/lib/queries.ts`
- Create: `frontend/src/components/ui/badge.tsx`, `dialog.tsx`, `textarea.tsx`, `select.tsx`, `table.tsx`

**Interfaces:**
- Produces: types `Item, Category, Technician, MovementType, ItemStatus, MovementLineInput, MovementResult, HistoryLine, History`; hooks `useItems, useCreateItem, useUpdateItem, useAdjustItem, useItemHistory, useCategories, useCreateCategory, useTechnicians, useCreateTechnician, useCreateMovement`; components `Badge, Dialog(+parts), Textarea, Select, Table(+parts)`.
- Consumes: `api`, `Page` (existing), `useQuery/useMutation/useQueryClient`.

- [ ] **Step 1: Extend `frontend/src/types.ts`** (append after the existing `Page<T>`)

```typescript
export type MovementType = "ENTRADA" | "SAIDA" | "AJUSTE_POS" | "AJUSTE_NEG";
export type ItemStatus = "Em falta" | "Ruim" | "Alerta" | "Bom";

export interface Item {
  id: string;
  sku: string;
  nome: string;
  category_id: string | null;
  unidade: string;
  estoque_minimo: number;
  saldo: number;
  ativo: boolean;
  observacoes: string;
  created_at: string;
  status: ItemStatus;
}

export interface Category {
  id: string;
  nome: string;
  parent_id: string | null;
  descricao: string;
  created_at: string;
}

export interface Technician {
  id: string;
  nome: string;
  ativo: boolean;
}

export interface MovementLineInput {
  item_id?: string | null;
  novo?: boolean;
  peca?: string;
  quantidade: number;
  categoria_id?: string | null;
  unidade?: string;
  estoque_minimo?: number;
  observacoes?: string;
  detalhes?: string;
}

export interface MovementResult {
  registros: number;
  novas_pecas: number;
  saldos: { item_id: string; nome: string; saldo: number }[];
}

export interface HistoryLine {
  id: string;
  data: string;
  tipo: MovementType;
  sinal: number;
  quantidade: number;
  tecnico: string;
  referencia: string;
  detalhes: string;
  saldo_resultante: number;
}

export interface History {
  item_id: string;
  nome: string;
  saldo: number;
  minimo: number;
  movimentacoes: HistoryLine[];
}
```

- [ ] **Step 2: Add the Radix Dialog dependency** — in `frontend/package.json`, add to `dependencies` (keep alphabetical-ish, keep everything else):

```json
    "@radix-ui/react-dialog": "^1.1.4",
```

- [ ] **Step 3: Create `frontend/src/lib/queries.ts`**

```typescript
import { api } from "@/lib/api";
import type {
  Category,
  History,
  Item,
  MovementLineInput,
  MovementResult,
  MovementType,
  Page,
  Technician,
} from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ---- Itens ----
export function useItems(q: string) {
  return useQuery({
    queryKey: ["items", q],
    queryFn: () => api<Page<Item>>("/items", { params: { q, size: 100 } }),
  });
}

export interface ItemInput {
  nome: string;
  sku?: string;
  category_id?: string | null;
  unidade?: string;
  estoque_minimo?: number;
  observacoes?: string;
}

export function useCreateItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ItemInput) => api<Item>("/items", { method: "POST", json: data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}

export function useUpdateItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ItemInput> & { ativo?: boolean } }) =>
      api<Item>(`/items/${id}`, { method: "PATCH", json: data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}

export function useAdjustItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, novo_saldo, motivo }: { id: string; novo_saldo: number; motivo: string }) =>
      api<Item>(`/items/${id}/adjust`, { method: "POST", json: { novo_saldo, motivo } }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["items"] });
      qc.invalidateQueries({ queryKey: ["history", vars.id] });
    },
  });
}

export function useItemHistory(id: string | null) {
  return useQuery({
    queryKey: ["history", id],
    queryFn: () => api<History>(`/items/${id}/history`),
    enabled: Boolean(id),
  });
}

// ---- Categorias ----
export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: () => api<Category[]>("/categories") });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) => api<Category>("/categories", { method: "POST", json: { nome } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

// ---- Técnicos ----
export function useTechnicians() {
  return useQuery({ queryKey: ["technicians"], queryFn: () => api<Technician[]>("/technicians") });
}

export function useCreateTechnician() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      api<Technician>("/technicians", { method: "POST", json: { nome } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["technicians"] }),
  });
}

// ---- Movimentação ----
export interface MovementInput {
  tipo: MovementType;
  referencia?: string;
  tecnico_id: string;
  itens: MovementLineInput[];
}

export function useCreateMovement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MovementInput) =>
      api<MovementResult>("/movements", { method: "POST", json: data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}
```

- [ ] **Step 4: Create `frontend/src/components/ui/badge.tsx`**

```typescript
import { cn } from "@/lib/utils";
import type { ItemStatus } from "@/types";

const STATUS_CLASS: Record<ItemStatus, string> = {
  Bom: "bg-success/15 text-success",
  Alerta: "bg-warning/15 text-warning",
  Ruim: "bg-orange-500/15 text-orange-400",
  "Em falta": "bg-destructive/15 text-destructive",
};

export function StatusBadge({ status }: { status: ItemStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        STATUS_CLASS[status],
      )}
    >
      {status}
    </span>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/ui/dialog.tsx`**

```typescript
import { cn } from "@/lib/utils";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;

export function DialogContent({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
      <DialogPrimitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2",
          "max-h-[calc(100vh-2rem)] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl",
          className,
        )}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogTitle({ children }: { children: ReactNode }) {
  return (
    <DialogPrimitive.Title className="mb-4 text-lg font-semibold tracking-tight">
      {children}
    </DialogPrimitive.Title>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/ui/textarea.tsx`**

```typescript
import { cn } from "@/lib/utils";
import { forwardRef, type TextareaHTMLAttributes } from "react";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
```

- [ ] **Step 7: Create `frontend/src/components/ui/select.tsx`** (styled native select)

```typescript
import { cn } from "@/lib/utils";
import { forwardRef, type SelectHTMLAttributes } from "react";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);
Select.displayName = "Select";
```

- [ ] **Step 8: Create `frontend/src/components/ui/table.tsx`**

```typescript
import { cn } from "@/lib/utils";
import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-xl border border-border">
      <table className={cn("w-full text-sm", className)} {...props} />
    </div>
  );
}

export function Th({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "bg-muted/50 px-4 py-2.5 text-left font-medium text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-t border-border px-4 py-2.5", className)} {...props} />;
}
```

- [ ] **Step 9: Install and build**

Run: `cd frontend && npm install` (pulls `@radix-ui/react-dialog`), then `npm run build`.
Expected: install succeeds; `tsc -b && vite build` clean, `dist/` produced. (No pages consume these yet — this task only adds the toolkit; the build must still pass with the new files present and unused-by-pages.)

> If `tsc` flags an unused export, that's fine at module level (exports aren't "unused locals"). If it flags an unused *import within a file*, fix that file. Do not disable `noUnusedLocals`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/types.ts frontend/package.json frontend/package-lock.json frontend/src/lib/queries.ts frontend/src/components/ui/badge.tsx frontend/src/components/ui/dialog.tsx frontend/src/components/ui/textarea.tsx frontend/src/components/ui/select.tsx frontend/src/components/ui/table.tsx
git commit -m "feat(frontend): parts data hooks, types and ui primitives (badge/dialog/select/table/textarea)"
```

---

### Task 2: Itens page — catalog, create, adjust

**Files:**
- Create: `frontend/src/components/item-form-dialog.tsx`, `frontend/src/components/adjust-dialog.tsx`
- Create: `frontend/src/pages/itens.tsx`
- Modify: `frontend/src/App.tsx` (add `/itens` route)

**Interfaces:**
- Consumes: hooks + primitives from Task 1; `Button`, `Input`, `Label`, `Card*` (existing); `toast` (sonner).
- Produces: `<ItensPage/>` at `/itens`.

- [ ] **Step 1: Create `frontend/src/components/item-form-dialog.tsx`** (criar peça)

```typescript
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
```

- [ ] **Step 2: Create `frontend/src/components/adjust-dialog.tsx`**

```typescript
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
```

- [ ] **Step 3: Create `frontend/src/pages/itens.tsx`**

```typescript
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
```

- [ ] **Step 4: Add the `useDebounce` hook if missing** — check `frontend/src/hooks/use-debounce.ts`. If it does NOT exist, create it:

```typescript
import { useEffect, useState } from "react";

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
```

- [ ] **Step 5: Add the route** — in `frontend/src/App.tsx`, import and add the `/itens` route inside the protected shell block (alongside the existing `/` dashboard route):

```typescript
import ItensPage from "@/pages/itens";
```
and inside the `<Route element={<Protected><AppShell/></Protected>}>` group:
```tsx
        <Route path="/itens" element={<ItensPage />} />
```
(The app-shell NAV already links to `/itens` from the foundation.)

- [ ] **Step 6: Build**

Run: `cd frontend && npm run build`
Expected: clean `tsc -b && vite build`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/item-form-dialog.tsx frontend/src/components/adjust-dialog.tsx frontend/src/pages/itens.tsx frontend/src/App.tsx frontend/src/hooks/use-debounce.ts
git commit -m "feat(frontend): itens catalog page with create and adjust dialogs"
```

---

### Task 3: Movimentar page — entrada/saída em lote

**Files:**
- Create: `frontend/src/pages/movimentar.tsx`
- Modify: `frontend/src/App.tsx` (add `/movimentar` route)
- Modify: `frontend/src/components/layout/app-shell.tsx` (add NAV item "Movimentar")

**Interfaces:**
- Consumes: `useItems, useTechnicians, useCreateMovement` (Task 1); `Button, Input, Select, Textarea, Card*, Label`; `toast`.
- Produces: `<MovimentarPage/>` at `/movimentar`.

- [ ] **Step 1: Create `frontend/src/pages/movimentar.tsx`**

```typescript
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { useCreateMovement, useItems, useTechnicians } from "@/lib/queries";
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

  const [tipo, setTipo] = useState<MovementType>("ENTRADA");
  const [tecnicoId, setTecnicoId] = useState("");
  const [referencia, setReferencia] = useState("");
  const [linhas, setLinhas] = useState<Linha[]>([linhaVazia()]);

  const itens = itensPage?.items ?? [];

  function atualizar(i: number, patch: Partial<Linha>) {
    setLinhas((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
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
```

- [ ] **Step 2: Add the route** — in `frontend/src/App.tsx`:

```typescript
import MovimentarPage from "@/pages/movimentar";
```
and inside the protected shell group:
```tsx
        <Route path="/movimentar" element={<MovimentarPage />} />
```

- [ ] **Step 3: Add the NAV item** — in `frontend/src/components/layout/app-shell.tsx`, add to the `NAV` array (import `ArrowLeftRight` from lucide-react):

```typescript
  { to: "/movimentar", label: "Movimentar", icon: ArrowLeftRight, end: false },
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/movimentar.tsx frontend/src/App.tsx frontend/src/components/layout/app-shell.tsx
git commit -m "feat(frontend): movimentar page (batch entrada/saida with on-the-fly item)"
```

---

### Task 4: Item history + final smoke test

**Files:**
- Create: `frontend/src/components/item-history-dialog.tsx`
- Modify: `frontend/src/pages/itens.tsx` (open history on row click)

**Interfaces:**
- Consumes: `useItemHistory` (Task 1), `Dialog*`, `Table*`, `Item`.
- Produces: `<ItemHistoryDialog/>` wired into the catalog.

- [ ] **Step 1: Create `frontend/src/components/item-history-dialog.tsx`**

```typescript
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
```

- [ ] **Step 2: Wire history into the catalog** — in `frontend/src/pages/itens.tsx`:
  1. Import: `import { ItemHistoryDialog } from "@/components/item-history-dialog";`
  2. Add state: `const [historico, setHistorico] = useState<Item | null>(null);`
  3. Make the "Peça" cell clickable to open history — change the name `<Td>` to:
     ```tsx
     <Td>
       <button
         className="font-medium text-primary hover:underline"
         onClick={() => setHistorico(item)}
       >
         {item.nome}
       </button>
     </Td>
     ```
  4. Render near the other dialogs: `<ItemHistoryDialog item={historico} onClose={() => setHistorico(null)} />`

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/item-history-dialog.tsx frontend/src/pages/itens.tsx
git commit -m "feat(frontend): per-item ledger history dialog"
```

- [ ] **Step 5: Manual smoke test (controller runs this, not a subagent)**

With backend running (`python run.py`) and a real Supabase login, start the frontend and drive the full flow in the in-app browser:
1. Login → dashboard.
2. Movimentar → Entrada, pick a technician, "Item novo" + name + qty 10 → Registrar → toast shows the new balance.
3. Itens → the new item appears with saldo 10 and a status pill.
4. Movimentar → Saída of 3 of that item → Itens shows saldo 7.
5. Click the item name → history shows Entrada 10 then Saída 3, saldo 7, most-recent first.
6. Ajustar → set saldo 5 → history gains an "Ajuste −" row, saldo 5.
Capture a screenshot of the catalog + history as proof.

---

## Self-Review

**1. Spec coverage (design §6 parts frontend):**
- Catalog with saldo + status pills + search (§6 "itens") → Tasks 1, 2. ✓
- Movement entrada/saída multi-line + new item on entrada (§6 "movimentar") → Task 3. ✓
- Per-item ledger history drawer (§6 "histórico do item") → Task 4. ✓
- Adjust balance from the UI (spec §5 adjust) → Task 2. ✓
- TanStack Query + react-router + theme tokens (§6) → all tasks. ✓
- Categories UI (create/assign) and machines/reports pages are out of scope here (later phases); category assignment on items is deferred (items can be created without a category — backend allows null).

**2. Placeholder scan:** No TBD. Each task ends in a concrete `npm run build`; the final task has an explicit manual smoke script with steps and expected results.

**3. Type consistency:** `Item.status` is `ItemStatus` (Task 1) consumed by `StatusBadge` (Task 1) and the catalog (Task 2). `useItems` returns `Page<Item>` matching the backend `Page[ItemOut]`. `useCreateMovement` input `MovementInput` mirrors the backend `MovementBatchIn` (tipo, referencia, tecnico_id, itens[]). `HistoryLine.sinal`/`saldo_resultante` match the backend `HistoryLineOut`. Native `<select>` used everywhere (no Radix Select); Radix Dialog only for modals — consistent with the constraint.
