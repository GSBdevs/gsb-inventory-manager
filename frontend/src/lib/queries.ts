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
