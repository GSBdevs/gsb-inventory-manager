# GrupoSB Estoque — memória do projeto

Gerenciador de estoque do Grupo SB (peças + máquinas), migrado do Google Apps Script.
Dono: Arthur (gruposb.dev@gmail.com). Idioma do produto: pt-BR. Commits: inglês, conventional.

## Stack
- Backend `backend/`: FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, PyJWT. Banco e auth no
  **Supabase** (Postgres gerenciado + Supabase Auth). SQLite fallback em dev/testes.
- Frontend `frontend/`: React 19, TS estrito, Vite 6, Tailwind 4 (tokens em `src/index.css`),
  UI shadcn-style à mão em `components/ui/`, TanStack Query 5, react-router 7, @supabase/supabase-js.
- Tema escuro único preto/cinza + amarelo `oklch(0.83 0.16 90)`; verde/vermelho só semânticos.

## Domínio (preservar do sistema antigo)
- Estoque **event-sourced**: `movements` é ledger append-only; saldo é derivado (`saldo_cache`
  é cache recomputável). Tipos: ENTRADA/SAIDA/AJUSTE_POS/AJUSTE_NEG.
- Dois módulos: peças (`items` + ledger) e máquinas (`machine_models` → `machine_units`).
- Papéis: `admin` | `operador`.

## Auth (Supabase)
- Login/sessão/refresh no **Supabase Auth** (front usa `@supabase/supabase-js`). O FastAPI só
  **valida o JWT** (HS256 com `SUPABASE_JWT_SECRET`, `aud=authenticated`) e resolve o `profiles`.
- 1º usuário logado vira `admin` (bootstrap); demais `operador`. Admin cria usuários via Admin API
  (`SUPABASE_SERVICE_ROLE_KEY`, só no backend). Promover manualmente: `scripts.set_admin`.

## Convenções e armadilhas
- Modelos herdam `TableBase` (UUID pk + created/updated). **`profiles.id` é o uuid do Supabase**
  (sem gerador default). Enums: StrEnum + `native_enum=False`.
- Banco em produção: **session pooler do Supabase (5432)** — servidor persistente, prepared
  statements OK. Modo transação (6543) é para serverless — evitado.
- Windows: psycopg async exige SelectorEventLoop → `app/core/aio.py` + `python run.py`.
- Migrações autogeradas contra SQLite scratch; revisar `server_default` em colunas NOT NULL novas.
- Datas: schemas Out usam `UTCDateTime` (`schemas/common.py`).
- Front: `lib/api.ts` pega o token da sessão do Supabase; 401 → signOut + /login. Paginação `Page<T>`.

## Receita p/ novo módulo
model → schemas → router (padrão `users.py`) → `api/router.py` → migração → teste → `types.ts` →
página → rota em `App.tsx` → item no `NAV` do `app-shell.tsx`.

## Comandos
```
backend: python run.py                 # API dev
backend: python -m pytest              # testes (sem Supabase)
backend: python -m scripts.set_admin <email>
frontend: npm run dev | npm run build
```

## Estado
Fundação (scaffold + Supabase Auth) implementada. Próximas fases: núcleo de peças (ledger),
máquinas, relatórios/dashboard, ETL da planilha. Ver `docs/superpowers/plans/`.
