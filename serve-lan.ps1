# Builda o frontend e sobe a API servindo a SPA (origem única) na rede local.
# Banco e auth ficam no Supabase (backend/.env). Uso: .\serve-lan.ps1
$ErrorActionPreference = "Stop"

Push-Location frontend
npm install
npm run build
Pop-Location

Push-Location backend
$env:FRONTEND_DIST = "../frontend/dist"
$env:API_HOST = "0.0.0.0"
Write-Host "Servindo em http://<ip-da-maquina>:8000 (origem única; DB/Auth = Supabase)"
.\.venv\Scripts\python run.py
Pop-Location
