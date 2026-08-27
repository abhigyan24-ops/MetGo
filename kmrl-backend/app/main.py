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

    # 0. Create all DB tables
    try:
        from app.db.session import Base
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Table creation skipped/failed: %s", exc)

    # 1. DB connectivity
    try:
        check_db_connection()
    except Exception as exc:
        logger.warning("Database check warning at startup: %s", exc)

    # 2. Auto-seed if empty
    try:
        from app.db.session import SessionLocal
        from app.models.train import Train
        with SessionLocal() as db:
            if db.query(Train).count() == 0:
                logger.info("Database is empty. Running automatic seed...")
                from app.seed.seed_fleet import seed_yard_layout, generate_trains_with_data
                from app.seed.seed_stations import parse_gtfs_stops, match_and_sequence_stations, seed_stations
                from pathlib import Path
                
                bays = seed_yard_layout(db)
                generate_trains_with_data(db, bays)
                
                stops_path = Path(__file__).parent.parent / "stops.txt"
                if stops_path.exists():
                    gtfs_stops = parse_gtfs_stops(stops_path)
                    stations_data = match_and_sequence_stations(gtfs_stops)
                    seed_stations(db, stations_data)
                logger.info("Automatic seed completed successfully.")
    except Exception as exc:
        logger.warning("Auto-seeding skipped: %s", exc)

    # 3. Create TimescaleDB hypertables (idempotent, only on Postgres)
    if not settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                create_timescale_hypertables(conn)
        except Exception as exc:
            logger.warning("Hypertable setup skipped: %s", exc)

    # 4. Neo4j connectivity
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
    allow_credentials=False,      # Fix: cannot use True with wildcard "*" origin
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
