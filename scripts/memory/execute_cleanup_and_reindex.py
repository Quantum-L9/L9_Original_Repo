#!/usr/bin/env python3
"""
execute_cleanup_and_reindex.py - Execute Cleanup and Re-index
==============================================================

Deletes trash embeddings and re-indexes high-value content.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Execute Cleanup and Re-index",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "execute_cleanup_and_reindex",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os
import sys
from pathlib import Path

import aiofiles
import structlog
from dotenv import load_dotenv

from core.decorators import must_stay_async

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


@must_stay_async("callers use await")
async def delete_trash_embeddings_from_sql():
    """Delete trash embeddings using the generated SQL."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set - cannot delete embeddings")
        logger.info("SQL file available at: /tmp/delete_trash.sql")
        return False

    try:
        import asyncpg

        # Read the SQL file
        sql_file = Path(__file__).parent / "delete_trash.sql"
        if not sql_file.exists():
            logger.error("SQL file not found. Run generate_delete_sql.py first")
            return False

        sql_content = sql_file.read_text()

        # Extract just the DELETE statement
        embedding_ids = []

        for line in sql_content.split("\n"):
            if line.strip().startswith("'") and line.strip().endswith("',"):
                eid = line.strip().rstrip(",").strip("'")
                embedding_ids.append(eid)
            elif "DELETE FROM semantic_memory" in line:
                pass

        if not embedding_ids:
            logger.warning("No embedding IDs found in SQL file")
            return False

        logger.info(f"Deleting {len(embedding_ids)} trash embeddings...")

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # Delete in batches
            batch_size = 100
            deleted = 0

            for i in range(0, len(embedding_ids), batch_size):
                batch = embedding_ids[i : i + batch_size]
                placeholders = ",".join([f"${j + 1}" for j in range(len(batch))])

                result = await conn.execute(
                    f"""
                    DELETE FROM semantic_memory
                    WHERE embedding_id::text IN ({placeholders})
                    """,  # noqa: S608 — placeholders are $N params, not user input
                    *batch,
                )
                deleted += int(result.split()[-1])

            logger.info(f"✅ Deleted {deleted} trash embeddings")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to delete embeddings: {e}", exc_info=True)
        return False


@must_stay_async("callers use await")
async def reindex_content():
    """Run all re-indexing scripts."""
    scripts = [
        ("GMP Reports", "scripts/index_gmp_reports.py"),
        ("Error Patterns", "scripts/index_error_patterns.py"),
        ("Architecture", "scripts/index_architecture.py"),
        ("Preferences", "scripts/index_preferences.py"),
        ("Tool Usage", "scripts/index_tool_usage.py"),
    ]

    results = {}

    for name, script_path in scripts:
        logger.info(f"Re-indexing {name}...")
        try:
            import subprocess

            result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
                [sys.executable, script_path, "--verbose"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"✅ {name} indexed successfully")
                results[name] = "success"
            else:
                logger.warning(f"⚠️  {name} indexing had issues: {result.stderr[:200]}")
                results[name] = "partial"

        except Exception as e:
            logger.error(f"❌ {name} indexing failed: {e}")
            results[name] = "failed"

    return results


async def main():
    """Main execution."""
    logger.info("\n" + "=" * 60)
    logger.info("cleanup and re-index execution")
    logger.info("=" * 60)
    logger.info("output", value="")

    # Step 1: Generate SQL
    logger.info("step 1: generating deletion sql...")
    import subprocess

    result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
        [sys.executable, "scripts/generate_delete_sql.py"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        async with aiofiles.open("/tmp/delete_trash.sql", "w") as f:  # noqa: S108 — intentional temp path for generated SQL
            await f.write(result.stdout)
        logger.info("  ✅ sql generated")
    else:
        logger.error("  ❌ failed to generate sql: {result.stderr[:200]}")
        return

    # Step 2: Delete trash embeddings
    logger.info("\nstep 2: deleting trash embeddings...")
    deleted = await delete_trash_embeddings_from_sql()

    if not deleted:
        logger.error("  ⚠️  could not delete (database_url not set or error)")
        logger.info("  sql file available at: /tmp/delete_trash.sql")
        logger.info("  run manually: psql -d l9 -f /tmp/delete_trash.sql")

    # Step 3: Re-index
    logger.info("\nstep 3: re-indexing high-value content...")
    results = await reindex_content()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("summary")
    logger.info("=" * 60)
    print(
        f"  Trash embeddings: {'✅ Deleted' if deleted else '⚠️  Manual deletion needed'}"
    )
    logger.info("\n  re-indexing results:")
    for name, status in results.items():
        icon = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"
        logger.info("    icon name: status", icon=icon, name=name, status=status)
    logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "batch-processing",
        "filesystem",
        "logging",
        "memory-substrate",
        "operations",
        "postgres",
        "service",
        "subprocess",
        "testing",
    ],
    "keywords": [
        "cleanup",
        "delete",
        "embeddings",
        "execute",
        "index",
        "reindex",
        "sql",
        "trash",
    ],
    "business_value": "Utility module for execute cleanup and reindex",
    "last_modified": "2026-01-17T23:47:56Z",
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
