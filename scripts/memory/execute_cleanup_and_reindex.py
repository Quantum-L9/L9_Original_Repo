#!/usr/bin/env python3
"""
execute_cleanup_and_reindex.py - Execute Cleanup and Re-index
==============================================================

Deletes trash embeddings and re-indexes high-value content.
"""

import os
import sys
import asyncio
import structlog
from pathlib import Path
from dotenv import load_dotenv
from core.decorators import must_stay_async

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


async def delete_trash_embeddings_from_sql():
    """Delete trash embeddings using the generated SQL."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set - cannot delete embeddings")
        logger.info("SQL file available at: /tmp/delete_trash.sql")
        return False

    try:
        import asyncpg

        # Read the SQL file
        sql_file = Path("/tmp/delete_trash.sql")
        if not sql_file.exists():
            logger.error("SQL file not found. Run generate_delete_sql.py first")
            return False

        sql_content = sql_file.read_text()

        # Extract just the DELETE statement
        delete_sql = None
        embedding_ids = []

        for line in sql_content.split("\n"):
            if line.strip().startswith("'") and line.strip().endswith("',"):
                eid = line.strip().rstrip(",").strip("'")
                embedding_ids.append(eid)
            elif "DELETE FROM semantic_memory" in line:
                delete_sql = line

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
                    """,
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

            result = subprocess.run(
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
    print("\n" + "=" * 60)
    print("CLEANUP AND RE-INDEX EXECUTION")
    print("=" * 60)
    print()

    # Step 1: Generate SQL
    print("Step 1: Generating deletion SQL...")
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/generate_delete_sql.py"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        with open("/tmp/delete_trash.sql", "w") as f:
            f.write(result.stdout)
        print("  ✅ SQL generated")
    else:
        print(f"  ❌ Failed to generate SQL: {result.stderr[:200]}")
        return

    # Step 2: Delete trash embeddings
    print("\nStep 2: Deleting trash embeddings...")
    deleted = await delete_trash_embeddings_from_sql()

    if not deleted:
        print("  ⚠️  Could not delete (DATABASE_URL not set or error)")
        print("  SQL file available at: /tmp/delete_trash.sql")
        print("  Run manually: psql -d l9 -f /tmp/delete_trash.sql")

    # Step 3: Re-index
    print("\nStep 3: Re-indexing high-value content...")
    results = await reindex_content()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(
        f"  Trash embeddings: {'✅ Deleted' if deleted else '⚠️  Manual deletion needed'}"
    )
    print("\n  Re-indexing results:")
    for name, status in results.items():
        icon = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"
        print(f"    {icon} {name}: {status}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
