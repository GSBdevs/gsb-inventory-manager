# Migração do Gerenciador de Estoque → inventory-manager

**Data:** 2026-08-07
**Autor/dono:** Arthur (gruposb.dev@gmail.com) — Grupo SB
**Idioma do produto:** pt-BR · **Commits:** inglês, conventional commits

## 1. Objetivo

Migrar o "Gerenciador de Estoque" que hoje roda em **Google Apps Script** (Sheets como
banco) para uma aplicação web robusta e independente, com banco relacional real, login
por papéis e melhor usabilidade. A stack-alvo **espelha o `gsb-crm`** (mesmo autor/empresa,
mesma identidade visual e mesma história de deploy) para máxima consistência e reaproveitamento.

Decisões do dono (2026-08-07):

- **Formato:** web app agora (modelo gsb-crm, SPA servida pela própria API), com casca
  PWA/Tauri adiada para depois — sem retrabalho de backend.
- **Dados:** migrar **tudo** via ETL (itens, ledger de movimentações, técnicos, categorias,
  máquinas e unidades), preservando o histórico.
- **Acesso:** login real multiusuário com papéis (JWT + Argon2, modelo gsb-crm).

## 2. Sistema atual (o que preservar)

Diagnóstico do código em `Documents/CODES/gerenciadorDeEstoque` (~6 mil linhas, Apps Script):

- **Estoque event-sourced.** A aba `MOVIMENTACOES` é um **ledger imutável (append-only)** e o
  saldo é **derivado**; `saldo_cache` no item é apenas otimização recomputável. Esta é a
  decisão de design mais importante e **deve ser preservada**.
- **Arquitetura já em camadas:** `Schema/repo → Servicos (negócio puro) → Api (controllers,
  envelope `{ok,data}`) → HTML`. A camada de serviço foi escrita para "migrar quase intacta
  para Node/Python"; a Api foi pensada para "virar rotas REST". A migração é, portanto,
  **reimplementar a mesma lógica noutra stack**, não redesenhar o domínio.
- **Dois domínios independentes:**
  1. **Peças** — `ITENS` + ledger `MOVIMENTACOES` (tipos ENTRADA/SAIDA/AJUSTE_POS/AJUSTE_NEG).
  2. **Máquinas** — `MAQUINAS` (modelo) → `UNIDADES_MAQUINA` (unidade física, com série,
     patrimônio, condição, localização, responsável).
- **Refatoração v1→v2 em andamento:** ainda há código v1 (abas `ESTOQUE/ENTRADA/SAIDA`). A
  migração **aposenta o v1** e adota apenas o modelo v2 (event-sourced).
- **Regras de negócio a portar** (de `Servicos.gs`/`Maquinas.gs`/`back.gs`):
  - Movimentação em lote: valida quantidade inteira/limite, valida disponibilidade **antes**
    de gravar, grava o ledger, atualiza o cache de saldo. Saída não pode exceder o disponível.
  - Criação de item on-the-fly na entrada; unicidade de nome (case/spacing-insensitive).
  - Ajuste de saldo gera lançamento no ledger (AJUSTE_POS/NEG), nunca edição destrutiva.
  - Status visual do saldo: `Em falta` (≤0) · `Ruim` (<mínimo) · `Alerta` (<2×mínimo) · `Bom`.
  - Renome de item **não** altera histórico (ledger referencia o id, não o nome).
  - Máquinas: modelo reutilizado por nome; unicidade de número de série entre unidades ativas;
    arquivar modelo arquiva as unidades; condições canônicas + valor custom aceito.
  - Relatório agrupado por tipo/dia/técnico/peça, com filtros de período
    (semanal/mensal/trimestral/anual/personalizado) e por técnico.

## 3. Arquitetura-alvo

Estrutura espelhando o `gsb-crm`:

```
inventory-manager/
  backend/                 # FastAPI + SQLAlchemy 2 async + Alembic + Pydantic v2
    app/
      core/                # config, database (Postgres/SQLite fallback), security (JWT/Argon2),
                           # deps, pagination, aio (SelectorEventLoop no Windows)
      models/              # TableBase (UUID + created/updated) → User, Category, Item, Movement,
                           # MachineCategory, MachineModel, MachineUnit
      schemas/             # <X>Create / <X>Update / <X>Out por módulo
      api/                 # auth, users, categories, items, movements, machines, reports
      services/            # inventory_service, machine_service, report_service  ← PORTE de Servicos.gs
      main.py
    alembic/               # migrações
    scripts/               # seed.py (admin + demo), import_sheets.py (ETL)
    tests/                 # pytest, SQLite in-memory
    run.py                 # entrypoint dev Windows + Postgres
  frontend/                # React 19 + TS estrito + Vite 6 + Tailwind 4
    src/
      components/ui/       # kit shadcn-style reaproveitado do gsb-crm
      components/layout/   # app-shell (sidebar + drawer mobile) + notificações
      pages/               # login, dashboard, itens, movimentar, maquinas, relatorios, usuarios
      context/auth.tsx     # sessão + refresh
      lib/api.ts           # fetch client com refresh single-flight + redirect 401
      types.ts
      index.css            # tokens de tema (preto/cinza/amarelo)
  docker-compose.yml       # db(5433) + (redis opcional) + api + frontend
  serve-lan.ps1            # build do front + origem única (API serve a SPA)
  README.md / CLAUDE.md / HANDOFF.md
```

**Deploy** (idêntico ao CRM): origem única (`FRONTEND_DIST` faz a API servir o build, sem CORS);
LAN + Cloudflare Tunnel para acesso externo; ou nuvem Render (API+SPA) + Neon (Postgres).

## 4. Modelo de dados

Todas as tabelas herdam `TableBase` (PK **UUID** + `created_at`/`updated_at`).

- **`users`** — `email` (único), `password_hash` (Argon2id), `nome`, `papel`
  (`admin` | `operador`), `ativo`.
- **`categories`** — `nome`, `parent_id` (nullable), `descricao`. (peças)
- **`items`** — `sku` (opcional, humano), `nome` (único normalizado), `category_id` (nullable),
  `unidade` (default `un`), `estoque_minimo`, `saldo_cache` (recomputável), `ativo`,
  `observacoes`, `legacy_id` (o `itm_…` de origem).
- **`movements`** (LEDGER, append-only, nunca editar/apagar) — `tipo`
  (StrEnum `ENTRADA`/`SAIDA`/`AJUSTE_POS`/`AJUSTE_NEG`, `native_enum=False`), `item_id`,
  `quantidade` (inteiro > 0), `usuario_id` (técnico, nullable p/ ajuste), `referencia`,
  `detalhes`, `registrado_por` (quem operou), `saldo_resultante`, `estorno_de` (nullable),
  `legacy_id` (o `mov_…` de origem).
- **`machine_categories`** — `nome`, `parent_id`, `descricao`.
- **`machine_models`** — `nome`, `machine_category_id`, `marca`, `modelo`, `ativo`,
  `observacoes`, `legacy_id` (`maq_…`).
- **`machine_units`** — `machine_model_id`, `numero_serie` (único entre ativas quando informado),
  `condicao`, `patrimonio`, `localizacao`, `responsavel`, `observacoes`, `ativo`,
  `legacy_id` (`umq_…`).

**Divergências deliberadas do Apps Script (aprovadas):**

1. **PK = UUID** (padrão `TableBase`) no lugar do sequencial `itm_/mov_`. O id antigo é
   preservado em `legacy_id` para rastreabilidade e para o ETL casar referências.
2. **Concorrência via transação + `SELECT … FOR UPDATE`** na linha do item (trava fina do
   Postgres), aposentando o `LockService` global. Mesma garantia anti-saldo-negativo sem
   serializar o sistema inteiro. No fallback SQLite (dev/teste), a transação serializa
   naturalmente.

**Enums:** `StrEnum` + `native_enum=False` (armazenam o NAME), como no gsb-crm.

## 5. API (REST)

Autenticadas por padrão (JWT bearer). Papel `admin` exigido em usuários e em ações sensíveis.

**Auth/Usuários**
- `POST /api/v1/auth/login` → access (15 min) + refresh (7d, rotação/revogação)
- `POST /api/v1/auth/refresh`
- `GET /api/v1/users` · `POST /api/v1/users` (admin) · `PATCH /api/v1/users/{id}`

**Peças**
- `GET /api/v1/categories` · `POST /api/v1/categories`
- `GET /api/v1/items` (busca `q`, filtro por categoria/status, paginado) · `POST` · `PATCH /items/{id}`
- `GET /api/v1/items/{id}/history` (ledger do item, mais recente primeiro)
- `POST /api/v1/items/{id}/adjust` (ajuste de saldo → lançamento no ledger)

**Movimentações**
- `POST /api/v1/movements` — payload em lote `{ tipo, referencia, itens: [{item_id|novo, quantidade, ...}] }`;
  valida disponibilidade antes de gravar; grava ledger; atualiza `saldo_cache`.

**Máquinas**
- `GET /api/v1/machines` (modelos com unidades agregadas + contagem por condição) · `POST /machines`
- `PATCH /api/v1/machines/{id}` · `POST /api/v1/machines/{id}/archive`
- `PATCH /api/v1/units/{id}` · `POST /api/v1/units/{id}/archive`
- `GET /api/v1/machine-categories` · `POST`

**Relatórios**
- `GET /api/v1/reports` (filtros: tipo, período, técnico; agrupamento tipo/dia/técnico/peça)
- `GET /api/v1/reports/alerts` (itens em estoque baixo)
- `GET /api/v1/reports/summary` (KPIs do dashboard: itens, alertas, máquinas em campo)

Erros: `HTTPException` com mensagem pt-BR; validação por Pydantic. Paginação `Page[T]`.

## 6. Frontend

- Tema escuro único preto/cinza + **amarelo** `oklch(0.83 0.16 90)`; verde/vermelho apenas
  semânticos. Tokens reaproveitados do `gsb-crm` (`index.css`), fonte Inter.
- Kit `components/ui` (estilo shadcn) e `lib/api.ts` (refresh automático, redirect 401)
  reaproveitados do gsb-crm.
- **Páginas:** `login`; `dashboard` (KPIs + alertas de estoque baixo); `itens` (catálogo com
  saldo e pílulas de status Bom/Alerta/Ruim/Em falta, busca/filtro); `movimentar`
  (entrada/saída multilinha, criar item novo na entrada); `histórico do item` (drawer do
  ledger); `máquinas` (cards de modelo → detalhe com unidades); `relatórios` (Recharts +
  filtros de período/técnico/tipo); `usuários` (admin).
- TanStack Query 5 (dados), react-router 7, remontagem de dialogs de formulário com `key`.

## 7. ETL — migração dos dados reais

`backend/scripts/import_sheets.py`:

- **Entrada:** export da planilha atual em `.xlsx`/CSV (abas v2: `ITENS`, `MOVIMENTACOES`,
  `USUARIOS`, `CATEGORIAS`, `MAQUINAS`, `UNIDADES_MAQUINA`, `CATEGORIAS_MAQUINAS`). O dono
  exporta (File → Download → .xlsx); o script consome o arquivo — sem credencial da Google API.
- **Processo:** idempotente; mapeia `legacy_id`; insere categorias → itens → **replay do ledger**
  em ordem cronológica → usuários/técnicos → máquinas/unidades.
- **Verificação:** ao final, recomputa o saldo derivado de cada item e **compara com o
  `saldo_cache` de origem**; divergências viram relatório explícito (não silêncio).
- **Reexecução:** `--reset` limpa e recarrega; sem flag, faz upsert por `legacy_id`.

## 8. Segurança e operação

- JWT access curto + refresh com rotação/revogação (tabela `refresh_tokens`); Argon2id (pwdlib).
- Rate-limit de login por IP (em memória, como no CRM); sem cadastro aberto (admin cria usuários).
- `ENV != dev` recusa subir com `SECRET_KEY` de dev.
- Origem única sem CORS na LAN; HTTPS via Cloudflare Tunnel/Tailscale (não terminado pela API).
- Windows: `app/core/aio.py` + `run.py` (SelectorEventLoop p/ psycopg async); hot-reload só no
  modo SQLite.

## 9. Testes

- Backend: `pytest` com SQLite in-memory (no estilo dos 16 testes do CRM). Cobrir: auth
  (rotação/revogação/rate-limit), movimentação (saldo derivado, saída insuficiente, item novo,
  ajuste), unicidade de item, máquinas (unicidade de série, arquivar modelo→unidades),
  relatórios (agrupamento/períodos), ETL (replay + verificação de saldo).
- Frontend: `tsc -b` + `vite build` limpos.

## 10. Plano de execução em fases

0. **Scaffold** — backend + frontend a partir do padrão gsb-crm, `docker-compose`, config,
   database (Postgres/SQLite), aio/run.py, main.py, saúde da API.
1. **Auth + usuários** — login, papéis, refresh, seed admin.
2. **Núcleo de peças** *(o coração)* — categorias, itens, ledger de movimentações com saldo
   derivado, ajuste, histórico.
3. **Máquinas** — modelos + unidades.
4. **Relatórios + alertas + dashboard**.
5. **ETL** — importador + verificação contra os dados reais exportados.
6. **Acabamento** — origem única (`serve-lan.ps1`), docs de deploy, README/CLAUDE/HANDOFF,
   gancho PWA (casca desktop fica para uma fase futura).

## 11. Fora de escopo (agora)

- Casca desktop (Tauri) e PWA instalável — previstos para depois, sem retrabalho do backend.
- Multi-tenancy/escopo de dados por usuário.
- Leitura de código de barras / etiquetas (candidato a fase futura, inspirado em PartKeepr/InvenTree).
- Workflows/automação (o CRM tem; aqui só se houver necessidade real).

## 12. Referências

- Molde principal: `gsb-crm` (FastAPI + React 19 + Tailwind 4 + Postgres). Molde de casca/PWA:
  `gsb-notes` (Vite + Tauri).
- Produtos de referência em features/UX: **InvenTree** (peças/stock com histórico),
  **Snipe-IT** (ativos por unidade), **Grocy/PartKeepr**.
