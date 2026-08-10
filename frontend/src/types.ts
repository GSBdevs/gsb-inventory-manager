export type UserRole = "admin" | "operador";

export interface Profile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

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
