# bootstrap/__main__.py
"""
Canonical L9 Bootstrap Entrypoint
Runs exactly once. Fails hard. Writes bootstrap artifact.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ---- CONFIG ----

REQUIRED_ENV = [
    "DATABASE_URL",
    "REDIS_URL",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
]

BOOTSTRAP_KEY = "l9.bootstrap"
BOOTSTRAP_VERSION = "2026-01-28"

# ---- UTIL ----


def fatal(msg: str) -> None:
    """Print fatal error message and exit with status 1.

    Args:
        msg: Error message to print to stderr.
    """
    print(f"[BOOTSTRAP:FATAL] {msg}", file=sys.stderr)  # noqa: ADR-0019
    sys.exit(1)


def ensure_asyncpg_url(url: str) -> str:
    """
    Ensure DATABASE_URL uses asyncpg driver for SQLAlchemy.
    Converts postgresql:// to postgresql+asyncpg://
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if "+asyncpg" not in url:
        fatal(f"DATABASE_URL must use asyncpg driver, got: {url[:50]}...")
    return url


def check_env() -> None:
    """Verify all required environment variables are set.

    Raises:
        SystemExit: If any required environment variables are missing.
    """
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        fatal(f"Missing required env vars: {missing}")


# ---- BOOTSTRAP STEPS ----


async def run_migrations(engine) -> None:
    """Run database migrations using the migration runner.

    Args:
        engine: SQLAlchemy async engine (unused, URL from env).
    """
    from memory.migration_runner import run_migrations as _run_migrations

    db_url = os.environ["DATABASE_URL"]
    await _run_migrations(db_url)


async def init_memory_substrate() -> None:
    """Initialize the memory substrate service."""
    from memory.substrate_service import init_service

    await init_service()


async def init_neo4j() -> None:
    """Initialize and verify Neo4j graph database connection."""
    from memory.graph_client import get_neo4j_client

    client = await get_neo4j_client()
    await client.verify_connectivity()


async def bootstrap_agent():
    """
    Bootstrap the primary L9 agent using 7-phase ceremony.
    Requires substrate service to be initialized first.
    """
    from core.agents.bootstrap.orchestrator import bootstrap_agent as _bootstrap_agent
    from core.agents.schemas import AgentConfig
    from memory.substrate_service import get_service

    # Get initialized substrate service
    substrate_service = await get_service()

    # Create default agent config for L9 primary agent
    config = AgentConfig(
        agent_id="l9-primary",
        name="L9 Primary Agent",
        personality_id="l9-standard-v1",
        model="gpt-4o",
        temperature=0.3,
        max_tokens=4000,
    )

    # Run 7-phase bootstrap ceremony
    await _bootstrap_agent(config, substrate_service)


async def write_bootstrap_artifact(engine) -> None:
    """Write bootstrap completion artifact to system_state table.

    Creates the system_state table if needed and records bootstrap
    version and timestamp. Uses ON CONFLICT DO NOTHING to prevent
    duplicate entries.

    Args:
        engine: SQLAlchemy async engine for database operations.
    """
    payload = {
        "version": BOOTSTRAP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value JSONB,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        )
        await conn.execute(
            text("""
                INSERT INTO system_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key) DO NOTHING
            """),
            {"key": BOOTSTRAP_KEY, "value": json.dumps(payload)},
        )


# ---- MAIN ----


async def main() -> None:
    """Execute the L9 bootstrap sequence.

    Runs exactly once, failing hard if bootstrap was already completed.
    Sequence: check env -> migrations -> memory substrate -> Neo4j -> agent -> artifact.

    Raises:
        SystemExit: If bootstrap already completed or required env vars missing.
    """
    check_env()

    # Ensure asyncpg driver for SQLAlchemy
    db_url = ensure_asyncpg_url(os.environ["DATABASE_URL"])
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM system_state WHERE key = :key"),
            {"key": BOOTSTRAP_KEY},
        )
        if result.first():
            fatal("Bootstrap already completed. Refusing to run twice.")

    print("[BOOTSTRAP] Running migrations")  # noqa: ADR-0019
    await run_migrations(engine)

    print("[BOOTSTRAP] Initializing memory substrate")  # noqa: ADR-0019
    await init_memory_substrate()

    print("[BOOTSTRAP] Initializing Neo4j")  # noqa: ADR-0019
    await init_neo4j()

    print("[BOOTSTRAP] Bootstrapping agent")  # noqa: ADR-0019
    await bootstrap_agent()

    print("[BOOTSTRAP] Writing bootstrap artifact")  # noqa: ADR-0019
    await write_bootstrap_artifact(engine)

    print("[BOOTSTRAP] SUCCESS")  # noqa: ADR-0019


if __name__ == "__main__":
    asyncio.run(main())
