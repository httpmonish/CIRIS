# CIRIS 1-Click Prototype Launcher
# Starts both FastAPI Backend (Port 8000) and Next.js Frontend (Port 3000) simultaneously

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         CIRIS CYBERCRIME INTELLIGENCE PLATFORM            " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; python -m src.main"

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting Next.js Frontend on http://127.0.0.1:3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Green
Write-Host "[OK] Both FastAPI Backend and Next.js Frontend are launching!" -ForegroundColor Green
Write-Host "     Backend:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "     Frontend: http://127.0.0.1:3000" -ForegroundColor White
Write-Host "------------------------------------------------------------" -ForegroundColor Green
