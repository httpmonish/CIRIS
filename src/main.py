"""
CIRIS - Cybercrime Intelligence & ATM Cash-out Interception System
FastAPI Main Application Server.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db.database import get_db_path
from src.db.seed_gis_data import seed_gis_database
from src.api.v1 import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ciris.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and warmup."""
    logger.info("Initializing CIRIS Geospatial Platform...")
    db_file = get_db_path()
    if not db_file.exists():
        logger.info("GIS Database not found at %s. Seeding database...", db_file)
        try:
            seed_gis_database(db_path=db_file, rebuild=False)
        except Exception as e:
            logger.error("Error during initial database seed: %s", e)
    else:
        logger.info("GIS Database verified at %s", db_file)

    yield
    logger.info("Shutting down CIRIS Geospatial Platform.")


app = FastAPI(
    title="CIRIS - GIS Engine & Map Data Platform",
    description="Geospatial Intelligence Backend for CIRIS SIH 2026. Provides high-performance GeoJSON map endpoints for cybercrime cases, predicted cash-out ATMs, money flow trajectories, risk hotspots, and nearby spatial search.",
    version="1.0.0",
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


@app.get("/", tags=["Health & Status"])
def root():
    return {
        "system": "CIRIS - Cybercrime Intelligence & ATM Cash-out Interception System",
        "phase": "Phase 3A: GIS Engine + Map Data Foundation",
        "status": "OPERATIONAL",
        "version": "1.0.0",
        "docs_url": "/docs",
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
            "gis_stats": "/api/v1/map/stats"
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
