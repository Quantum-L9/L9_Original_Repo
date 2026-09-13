#!/usr/bin/env python3
"""
delete_trash_via_service.py - Delete Trash Embeddings via Memory Substrate Service
===================================================================================

Uses memory substrate service to delete trash embeddings.
Works with VPS database via DATABASE_URL.

Usage:
    python3 scripts/delete_trash_via_service.py
"""


import asyncio
import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


async def delete_trash_embeddings():
    """Delete trash embeddings using substrate repository."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        logger.info("Set DATABASE_URL in .env or environment")
        return False

    try:
        import asyncpg

        logger.info("Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)

        try:
            # Read embedding IDs from SQL file
            sql_file = Path(__file__).parent / "delete_trash.sql"
            if not sql_file.exists():
                logger.error("SQL file not found. Run generate_delete_sql.py first")
                return False

            # Extract IDs from SQL file
            embedding_ids = []
            for line in sql_file.read_text().split("\n"):
                line = line.strip()
                if line.startswith("'") and (line.endswith("',") or line.endswith("'")):
                    eid = line.rstrip(",").strip("'")
                    if eid and len(eid) == 36:  # UUID length
                        embedding_ids.append(eid)

            if not embedding_ids:
                logger.warning("No embedding IDs found in SQL file")
                return False

            logger.info(f"Found {len(embedding_ids)} trash embedding IDs to delete")

            # Delete in batches
            batch_size = 100
            total_deleted = 0

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

                deleted = int(result.split()[-1])
                total_deleted += deleted
                logger.info(
                    f"Deleted batch {i // batch_size + 1}: {deleted} embeddings"
                )

            logger.info(f"✅ Successfully deleted {total_deleted} trash embeddings")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to delete embeddings: {e}", exc_info=True)
        return False


async def main():
    """Main function."""
    logger.info("\n" + "=" * 60)
    logger.info("delete trash embeddings")
    logger.info("=" * 60)
    success = await delete_trash_embeddings()

    if success:
        logger.info("\n✅ trash embeddings deleted successfully")
        logger.info(
            "\nnext: run re-indexing scripts to populate with high-value content"
        )
    else:
        logger.error("\n❌ deletion failed - check logs above")
        logger.info("\nalternative: run sql manually:")
        logger.info("  psql -d l9_memory -f /tmp/delete_trash.sql")
        print(
            "  Or via Docker: docker exec -i l9-postgres psql -U l9_user -d l9_memory < /tmp/delete_trash.sql"
        )

    logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

# Runtime execution trace - updated automatically on every execution
