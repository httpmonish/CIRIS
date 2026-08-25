"""
CIRIS FastAPI Application Entry Point.

Productization backend exposing predictive cybercrime investigation APIs,
PostgreSQL persistence, frozen CIRIS ML V4 pipeline orchestration,
alert workflows, intervention decision support, and GeoJSON GIS services.
"""

import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.db.schema import setup_database
from src.services.intelligence_service import IntelligenceService

from src.api.v1.cases import router as cases_router
from src.api.v1.entities import router as entities_router
from src.api.v1.transactions import router as transactions_router
from src.api.v1.atms import router as atms_router
from src.api.v1.alerts import router as alerts_router
from src.api.v1.intervention import router as intervention_router
from src.api.v1.gis import router as gis_router
from src.api.v1.networks import router as networks_router
from src.api.v1.system import router as system_router

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ciris.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing DB tables and frozen ML pipeline once at startup."""
    logger.info("Initializing CIRIS Productization Backend...")
    setup_database()

    # Load frozen CIRIS ML V4 Pipeline Engine once
    intel_svc = IntelligenceService.get_instance()
    intel_svc.initialize()

    yield

    logger.info("Shutting down CIRIS Backend Service...")


app = FastAPI(
    title="CIRIS — Predictive Cybercrime Intelligence Platform",
    description=(
        "Proactive intelligence layer around cash-withdrawal and cybercrime predictions. "
        "Transforms fraud complaints into structured case intelligence, money-flow graphs, "
        "mule entity resolution, endpoint risk predictions, TreeSHAP evidence, and intervention recommendations."
    ),
    version="4.0.0-phase2",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration - Prevent allow_origins=["*"] in production settings
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Structured Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        f"REQ_ID={request_id} METHOD={request.method} PATH={request.url.path} "
        f"STATUS={response.status_code} LATENCY={duration_ms:.2f}ms"
    )
    response.headers["X-Request-ID"] = request_id
    return response


# Global Exception Handler returning clean structured JSON (no stack traces exposed to clients)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled exception for REQ_ID={request_id}: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred while processing the request.",
            "request_id": request_id,
        },
    )


# Root landing route
@app.get("/")
def root():
    """Root route welcoming users and directing to OpenAPI Swagger UI."""
    return {
        "title": "CIRIS — Predictive Cybercrime Intelligence Platform API",
        "status": "ONLINE",
        "swagger_docs": "/docs",
        "redoc_docs": "/redoc",
        "health_check": "/health",
        "system_status": "/api/v1/system/status",
        "demo_case": "/api/v1/cases/CASE-DEMO-001/intelligence",
    }


# Include API v1 Routers under /api/v1
app.include_router(cases_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(atms_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(intervention_router, prefix="/api/v1")
app.include_router(gis_router, prefix="/api/v1")
app.include_router(networks_router, prefix="/api/v1")
app.include_router(system_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
