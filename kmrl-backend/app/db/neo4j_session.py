"""
Neo4j Community Edition driver session management.
Self-hosted via Docker — no paid cloud tier used.
"""

from neo4j import GraphDatabase, Driver
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


class Neo4jSession:
    """Thin wrapper around the Neo4j driver for connection lifecycle management."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def session(self):
        """Return a new Neo4j session for use in a `with` block."""
        return self._driver.session()

    @retry(stop=stop_after_attempt(1), wait=wait_fixed(1))
    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()
        logger.info("Neo4j connection OK")

    def run(self, query: str, **params):
        """Execute a single Cypher query and return all records."""
        with self.session() as s:
            result = s.run(query, **params)
            return result.data()


@lru_cache()
def get_neo4j() -> Neo4jSession:
    """Return a cached Neo4j driver singleton."""
    settings = get_settings()
    return Neo4jSession(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
