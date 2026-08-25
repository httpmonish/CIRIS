# PowerShell script to seed demo data and launch CIRIS Prototype API Server
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "LAUNCHING CIRIS PHASE 2 PROTOTYPE BACKEND" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "."

Write-Host "`n[1/2] Seeding Demo Cases (CASE-DEMO-001 and CASE-DEMO-002)..." -ForegroundColor Yellow
python scripts/seed_demo.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Seeding failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/2] Starting FastAPI Server on http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "OpenAPI Swagger UI available at: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
