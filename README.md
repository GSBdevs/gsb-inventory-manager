# GrupoSB Estoque

Gerenciador de estoque (peças + máquinas) do Grupo SB. Migração do sistema em Google Apps
Script para uma aplicação web independente. Backend FastAPI usando **Supabase** como Postgres
gerenciado e provedor de autenticação (Supabase Auth).

**Stack:** FastAPI + SQLAlchemy async (Python) · React 19 + TS + Vite + Tailwind 4 · Supabase
(Postgres + Auth). SQLite como fallback de dev.

## Pré-requisitos

- Um projeto **Supabase** (grátis). Anote em Project Settings → API: `Project URL`,
  `anon key`, `service_role key` e o `JWT secret`.

## Rodar em dev

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -e ".[dev]"
copy .env.example .env            # preencha SUPABASE_URL / SUPABASE_JWT_SECRET / SERVICE_ROLE_KEY
python run.py                     # http://127.0.0.1:8000 (docs: /api/v1/docs)

# Frontend (outro terminal)
cd frontend
npm install
copy .env.example .env.local      # preencha VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
npm run dev                       # http://localhost:5173
```

O **primeiro usuário que logar** vira `admin` automaticamente. Crie usuários no painel do
Supabase (Authentication → Users) ou, como admin, via `POST /api/v1/users`. Para promover
alguém a admin manualmente: `python -m scripts.set_admin email@dominio.com`.

## Testes

```bash
cd backend && .venv\Scripts\python -m pytest    # não exige Supabase (JWT de teste local)
cd frontend && npm run build                    # type-check + build
```

## Rede local (origem única)

`.\serve-lan.ps1` builda o front e sobe a API servindo a SPA em `http://<ip>:8000`.

Consulte `docs/superpowers/specs/` (design) e `docs/superpowers/plans/` (planos por fase).
