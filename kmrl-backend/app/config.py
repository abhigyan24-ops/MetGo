"""
Application configuration loaded from environment variables.
Defaults are set for local Docker Compose development.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    deployment_mode: str = "docker"  # 'docker' for Celery/Redis queue, 'render' / 'sync' for synchronous in-process
    secret_key: str = "change_me_in_production"

    # PostgreSQL / TimescaleDB
    database_url: str = "postgresql://kmrl:kmrl_secret@localhost:5432/kmrl_db"

    # Redis (Self-hosted / Local)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    def __init__(self, **values):
        super().__init__(**values)
        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = "redis://localhost:6379/1"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "kmrl_neo4j_secret"

    # KMRL operational constants (hardcoded ground-truth values)
    kmrl_fleet_size: int = 25
    kmrl_station_count: int = 25
    kmrl_operating_hours_start: str = "06:00"
    kmrl_operating_hours_end: str = "22:00"
    kmrl_peak_headway_minutes: int = 8
    kmrl_line_length_km: float = 27.96
    kmrl_top_speed_kmh: int = 80
    kmrl_design_speed_kmh: int = 90
    kmrl_avg_speed_kmh: int = 35

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
