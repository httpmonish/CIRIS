"""
CIRIS - Cybercrime Intelligence & ATM Cash-out Interception System
FastAPI Main Application Server.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from src.db.database import get_db_path
from src.db.seed_gis_data import seed_gis_database
from src.db.auth_db import seed_default_auth_data
from src.security.auth import hash_password
from src.api.v1 import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ciris.main")

# Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "CIRIS REAL SIH PROJECT FRONTEND"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and warmup."""
    logger.info("Initializing CIRIS Geospatial Platform & RBAC Security Layer...")
    db_file = get_db_path()
    if not db_file.exists():
        logger.info("GIS Database not found at %s. Seeding database...", db_file)
        try:
            seed_gis_database(db_path=db_file, rebuild=False)
        except Exception as e:
            logger.error("Error during initial database seed: %s", e)
    else:
        logger.info("GIS Database verified at %s", db_file)

    # Initialize Auth & RBAC tables and demo accounts
    try:
        seed_default_auth_data(hash_func=hash_password)
        logger.info("Authentication & RBAC tables & demo accounts initialized.")
    except Exception as e:
        logger.error("Error initializing auth database: %s", e)

    yield
    logger.info("Shutting down CIRIS Geospatial Platform.")


app = FastAPI(
    title="CIRIS - Search-Space Reduction & ATM Interception Engine",
    description="Geospatial & Machine Learning Intelligence Backend for CIRIS (SIH 2026). Narrows 7,000 candidate ATMs to a ranked Top-10 shortlist in <50ms, capturing the true cash-out location 63.6% of the time (84.93% candidate pool recall) with Platt-calibrated confidence tiers.",
    version="1.1.0",
    lifespan=lifespan
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router)

# Mount static files for frontend assets if directory exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["UI & Dashboard"])
def index():
    """Serve the CIRIS interactive intelligence frontend dashboard."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return root()


@app.get("/api-info", tags=["Health & Status"])
def root():
    return {
        "system": "CIRIS - Cybercrime Intelligence & ATM Cash-out Interception System",
        "phase": "Phase 3A/4: GIS Engine + Operational Intelligence",
        "status": "OPERATIONAL",
        "version": "1.0.0",
        "docs_url": "/docs",
        "frontend_url": "/",
        "api_v1_base": "/api/v1",
        "endpoints": {
            "cases": "/api/v1/map/cases",
            "predicted_atms": "/api/v1/map/predicted-atms",
            "risk_heatmap": "/api/v1/map/risk",
            "money_flow_networks": "/api/v1/map/networks",
            "merchants": "/api/v1/map/merchants",
            "nearby_search": "/api/v1/map/nearby",
            "viewport_query": "/api/v1/map/viewport",
            "layer_definitions": "/api/v1/map/layers",
            "gis_stats": "/api/v1/map/stats",
            "alerts": "/api/v1/alerts",
            "investigations": "/api/v1/cases/search"
        }
    }


@app.get("/health", tags=["Health & Status"])
def health():
    db_file = get_db_path()
    return {
        "status": "healthy",
        "database_connected": db_file.exists(),
        "database_path": str(db_file)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
