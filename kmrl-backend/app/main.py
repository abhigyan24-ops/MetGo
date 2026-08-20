"""
MetGo — AI-Driven Train Induction Planning · FastAPI application entry point.

Data attribution:
    Contains data provided by Kochi Metro Rail Limited.
    Station topology, fleet size, and route structure are sourced from
    KMRL's official GTFS open data feed (https://kochimetro.org/open-data/).
    Maintenance and yard operations data is simulated in the shape KMRL's
    internal systems would produce, as that layer is operationally confidential.

Tech stack (all free / open-source):
    FastAPI · PostgreSQL · TimescaleDB CE · Neo4j CE · Redis · Celery · OR-Tools
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import check_db_connection, create_timescale_hypertables, engine
from app.db.neo4j_session import get_neo4j
from app.routers import plan, trains, stations, tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks, then yield to serve requests, then clean up."""
    logger.info("=== MetGo backend starting ===")

    # 1. Postgres connectivity
    try:
        check_db_connection()
    except Exception as exc:
        logger.warning("Postgres not ready at startup: %s", exc)

    # 2. Create TimescaleDB hypertables (idempotent)
    try:
        with engine.connect() as conn:
            create_timescale_hypertables(conn)
    except Exception as exc:
        logger.warning("Hypertable setup skipped: %s", exc)

    # 3. Neo4j connectivity
    try:
        get_neo4j().verify_connectivity()
    except Exception as exc:
        logger.warning("Neo4j not ready at startup: %s", exc)

    logger.info("=== Startup complete — serving requests ===")
    yield

    # Shutdown
    try:
        get_neo4j().close()
    except Exception:
        pass
    logger.info("=== MetGo backend shut down ===")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MetGo — Train Induction Planning API",
    description=(
        "AI-driven scheduling and yard induction planning for Kochi Metro Rail Limited. "
        "Station and route data: KMRL GTFS open data. "
        "Maintenance/yard data: simulated. "
        "Contains data provided by Kochi Metro Rail Limited."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Track C React dashboard on any local port during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(plan.router,     prefix="/plan",     tags=["Planning"])
app.include_router(trains.router,   prefix="/trains",   tags=["Fleet"])
app.include_router(stations.router, prefix="/stations", tags=["Stations"])
app.include_router(tasks.router,    prefix="/tasks",    tags=["Async Tasks"])


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "MetGo — Train Induction Planning API",
        "status": "ok",
        "attribution": "Contains data provided by Kochi Metro Rail Limited",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe — always 200 if the process is running."""
    return {"status": "ok"}
