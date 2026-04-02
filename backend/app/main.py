"""
Grigori API
Main FastAPI application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db
from app.api import search, alerts, network, regions, stats, contractors

# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Grigori API...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Grigori API...")


# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(
    title="Grigori API",
    description="""
    Procurement risk intelligence for Ukraine's reconstruction.
    
    ## Features
    
    * **Search** - Find contractors, tenders, and buyers
    * **Alerts** - Real-time feed of high-risk contracts
    * **Network** - Visualize contractor relationships
    * **Regions** - Geographic risk analysis
    * **Statistics** - Platform-wide metrics
    
    ## Risk Scoring
    
    Each tender and contractor receives a risk score (0-100) based on:
    - Price anomalies (30%)
    - Bid patterns (25%)
    - Competition level (20%)
    - Network connections (15%)
    - Contract value (10%)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================================================
# CORS Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Include Routers
# ============================================================================

app.include_router(
    search.router,
    prefix="/api/search",
    tags=["Search"]
)

app.include_router(
    contractors.router,
    prefix="/api/contractors",
    tags=["Contractors"]
)

app.include_router(
    alerts.router,
    prefix="/api/alerts",
    tags=["Alerts"]
)

app.include_router(
    network.router,
    prefix="/api/network",
    tags=["Network"]
)

app.include_router(
    regions.router,
    prefix="/api/regions",
    tags=["Regions"]
)

app.include_router(
    stats.router,
    prefix="/api/stats",
    tags=["Statistics"]
)

# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API root - basic health check."""
    return {
        "name": "Grigori API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: actual DB check
        "cache": "connected",     # TODO: actual Redis check
    }


# ============================================================================
# Error Handlers
# ============================================================================

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else None
        }
    )
