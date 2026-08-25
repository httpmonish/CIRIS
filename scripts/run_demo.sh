#!/usr/bin/env bash
# Shell script to seed demo data and launch CIRIS Prototype API Server
set -e

echo "============================================================"
echo "LAUNCHING CIRIS PHASE 2 PROTOTYPE BACKEND"
echo "============================================================"

export PYTHONPATH="."

echo -e "\n[1/2] Seeding Demo Cases (CASE-DEMO-001 and CASE-DEMO-002)..."
python scripts/seed_demo.py

echo -e "\n[2/2] Starting FastAPI Server on http://127.0.0.1:8000..."
echo "OpenAPI Swagger UI available at: http://127.0.0.1:8000/docs"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
