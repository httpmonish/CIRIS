@echo off
echo ============================================================
echo          CIRIS CYBERCRIME INTELLIGENCE PLATFORM           
echo ============================================================
echo.
echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000...
start cmd /k "cd /d %~dp0 && python -m src.main"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Next.js Frontend on http://127.0.0.1:3000...
start cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo [OK] Launching both servers!
echo      Backend:  http://127.0.0.1:8000/docs
echo      Frontend: http://127.0.0.1:3000
echo ============================================================
