"""
L9 Memory - Migration Runner
Version: 1.0.0

Automatic, idempotent database migration execution.
Tracks applied migrations in schema_migrations table.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Migration Runner",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-14T18:19:41Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "migration_runner",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["api.server", "mcp_memory.src.main"],
    },
}
# ============================================================================

import json
import os
from pathlib import Path

import asyncpg
import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


async def _init_json_codecs(conn: asyncpg.Connection) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


class MigrationRunner:
    """
    Runs database migrations automatically and idempotently.

    Tracks applied migrations in schema_migrations table.
    """

    def __init__(self, database_url: str, migrations_dir: str | None = None):
        """
        Initialize migration runner.

        Args:
            database_url: Postgres connection string
            migrations_dir: Path to migrations directory (defaults to ./migrations)
        """
        self._database_url = database_url
        self._migrations_dir = (
            Path(migrations_dir)
            if migrations_dir
            else Path(__file__).parent.parent / "migrations"
        )
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=2,
                init=_init_json_codecs,  # Register JSON codecs for JSONB columns
            )
            logger.info("Migration runner connected to database with JSON codecs")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Migration runner disconnected")

    async def ensure_migrations_table(self) -> None:
        """Create schema_migrations table if it doesn't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_name TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            logger.debug("Migrations table ensured")

    async def get_applied_migrations(self) -> set[str]:
        """Get set of already-applied migration names."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT migration_name FROM schema_migrations")
            return {row["migration_name"] for row in rows}

    async def mark_migration_applied(self, migration_name: str) -> None:
        """Mark a migration as applied."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES ($1) ON CONFLICT DO NOTHING",
                migration_name,
            )

    def get_migration_files(self) -> list[tuple[str, Path]]:
        """
        Get sorted list of migration files.

        Returns:
            List of (migration_name, file_path) tuples, sorted by name
        """
        if not self._migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self._migrations_dir}")
            return []

        migrations = []
        for file_path in sorted(self._migrations_dir.glob("*.sql")):
            migration_name = file_path.name
            migrations.append((migration_name, file_path))

        return migrations

    async def run_migration(self, migration_name: str, file_path: Path) -> bool:
        """
        Execute a single migration file.

        Args:
            migration_name: Name of the migration
            file_path: Path to SQL file

        Returns:
            True if migration was applied, False if already applied
        """
        logger.info(f"Running migration: {migration_name}")

        # Read SQL file
        sql_content = file_path.read_text()

        # Execute in transaction
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(sql_content)
            await self.mark_migration_applied(migration_name)

        logger.info(f"Migration applied: {migration_name}")
        return True

    async def run_all(self) -> dict[str, any]:
        """
        Run all pending migrations.

        Returns:
            Dict with status and counts
        """
        await self.connect()
        await self.ensure_migrations_table()

        applied = await self.get_applied_migrations()
        migration_files = self.get_migration_files()

        pending = []
        skipped = []
        errors = []

        for migration_name, file_path in migration_files:
            if migration_name in applied:
                skipped.append(migration_name)
                logger.debug(f"Skipping already-applied migration: {migration_name}")
                continue

            try:
                await self.run_migration(migration_name, file_path)
                pending.append(migration_name)
            except Exception as e:
                logger.error(f"Migration failed: {migration_name}: {e}")
                errors.append({"migration": migration_name, "error": str(e)})

        return {
            "status": "ok" if not errors else "error",
            "applied": len(pending),
            "skipped": len(skipped),
            "errors": len(errors),
            "pending_migrations": pending,
            "skipped_migrations": skipped,
            "error_details": errors,
        }


# Singleton instance
_runner: MigrationRunner | None = None


@must_stay_async("callers use await")
async def run_migrations(database_url: str | None = None) -> dict[str, any]:
    """
    Run all pending migrations.

    Args:
        database_url: Optional database URL (defaults to MEMORY_DSN env var)

    Returns:
        Migration result dict
    """
    global _runner

    if database_url is None:
        database_url = os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "No database URL provided. Set MEMORY_DSN or DATABASE_URL environment variable."
            )

    _runner = MigrationRunner(database_url)
    result = await _runner.run_all()
    await _runner.disconnect()

    return result


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-035",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "debugging",
        "filesystem",
        "learning",
        "logging",
        "memory-substrate",
        "migration",
        "postgres",
        "serialization",
        "service",
    ],
    "keywords": [
        "all",
        "applied",
        "connect",
        "disconnect",
        "ensure",
        "files",
        "mark",
        "memory",
    ],
    "business_value": "Implements MigrationRunner for migration runner functionality",
    "last_modified": "2026-01-14T18:19:41Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
