# CIRIS Phase 2 Prototype Runbook

## Prerequisites
- Python 3.10+ installed
- PostgreSQL + PostGIS (Optional, SQLite automatically used if PostgreSQL is not active)
- Python packages installed: `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `pydantic`, `pandas`, `lightgbm`, `shap`

---

## Startup Instructions

### Option 1: One-Click PowerShell Script (Windows)
```powershell
.\scripts\run_demo.ps1
```

### Option 2: One-Click Shell Script (Linux / macOS / Bash)
```bash
bash scripts/run_demo.sh
```

### Option 3: Manual Command Line Execution
1. **Seed Demo Data**:
   ```bash
   python scripts/seed_demo.py
   ```
2. **Start FastAPI Backend**:
   ```bash
   python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```

---

## Verification & Interactive Documentation
- **OpenAPI Swagger UI**: Open `http://127.0.0.1:8000/docs` in your browser.
- **ReDoc UI**: Open `http://127.0.0.1:8000/redoc`.
- **System Status Check**: Navigate to `http://127.0.0.1:8000/api/v1/system/status`.

---

## Resetting Demo Data
To reset the prototype database:
```bash
python scripts/reset_demo.py
```
