"""
PostgreSQL / TimescaleDB session management via SQLAlchemy.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=(settings.app_env == "development"),
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,       # recycle stale connections
        pool_size=10,
        max_overflow=20,
        echo=(settings.app_env == "development"),
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""
    pass


def get_db():
    """
    FastAPI dependency that yields a database session and guarantees cleanup.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def check_db_connection() -> None:
    """Verify the database is reachable — used at startup."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL connection OK")


def create_timescale_hypertables(conn) -> None:
    """
    Convert time-series tables to TimescaleDB hypertables after creation.
    Safe to call multiple times (IF NOT EXISTS guard).
    TimescaleDB is the free Community Edition run via Docker.
    """
    hypertable_statements = [
        # Mileage snapshots — one row per train per day
        """
        SELECT create_hypertable(
            'mileage_snapshots', 'recorded_at',
            if_not_exists => TRUE
        );
        """,
        # Fitness cert countdown events
        """
        SELECT create_hypertable(
            'cert_events', 'event_at',
            if_not_exists => TRUE
        );
        """,
    ]
    for stmt in hypertable_statements:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception as exc:
            # Non-fatal: TimescaleDB extension may not be loaded yet
            logger.warning("Hypertable creation skipped: %s", exc)
