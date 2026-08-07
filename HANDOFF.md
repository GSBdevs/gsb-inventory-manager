# HANDOFF — GrupoSB Estoque

## Última sessão
Fundação implementada a partir do plano `docs/superpowers/plans/2026-08-07-foundation-scaffold-auth.md`:
- Backend FastAPI: config (Supabase), async DB (Supabase Postgres/SQLite), `TableBase`,
  validação do JWT do Supabase, `profiles` com provisionamento + bootstrap do 1º admin,
  `/auth/me`, users CRUD (admin, criação via Supabase Admin API), `set_admin`, migração baseline.
- Frontend React/Vite/Tailwind 4: tema, client supabase-js, api client, auth context,
  login (Supabase), app-shell, dashboard placeholder, rotas protegidas.
- Testes backend passando (security, auth, users) sem exigir Supabase. `npm run build` limpo.

## Como validar
`cd backend && python -m pytest` · `cd frontend && npm run build` · login manual (exige projeto Supabase).

## Próximos passos (nova fase, novo plano)
1. **Núcleo de peças**: `Category`, `Item`, `Movement` (ledger), serviço de movimentação com saldo
   derivado + trava por transação (`SELECT ... FOR UPDATE` no Postgres do Supabase), ajuste, histórico.
2. **Máquinas**: `MachineModel` + `MachineUnit`.
3. **Relatórios + alertas + dashboard** (Recharts).
4. **ETL**: `scripts/import_sheets.py` — importar o export `.xlsx` da planilha e conferir saldos.

## Pendências conhecidas
- `backend/Dockerfile` ainda não criado (compose `api` depende dele) — fazer na fase de deploy.
- JWKS/chaves assimétricas do Supabase: hoje validamos HS256 com o JWT secret; migrar p/ JWKS é opcional.
- HTTPS não terminado pela API — em rede local usar Cloudflare Tunnel/Tailscale.
