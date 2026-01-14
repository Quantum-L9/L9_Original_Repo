#!/usr/bin/env python3
"""
delete_trash_embeddings.py - Delete Trash Embeddings via Substrate Service
==========================================================================

Uses memory substrate service to find and delete trash embeddings.
More reliable than direct DB access.

Usage:
    python3 scripts/delete_trash_embeddings.py [--dry-run] [--verbose]
"""

import os
import sys
import asyncio
import structlog
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")

# Error message patterns
ERROR_PATTERNS = [
    "Sorry, I encountered a temporary error. Please try again.",
    "Sorry, I encountered an error processing your command.",
    "No response generated.",
    "This message has already been processed.",
]


async def delete_trash_embeddings(
    database_url: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Delete trash embeddings using direct DB connection."""
    try:
        import asyncpg
        import json as json_lib
        
        conn = await asyncpg.connect(database_url)
        try:
            # Get all embeddings
            rows = await conn.fetch("""
                SELECT 
                    embedding_id,
                    payload::text as payload_json
                FROM semantic_memory
            """)
            
            logger.info(f"Scanning {len(rows)} embeddings...")
            
            trash_ids = []
            
            for row in rows:
                try:
                    payload = json_lib.loads(row["payload_json"]) if row["payload_json"] else {}
                    
                    text = (
                        payload.get("_text") or
                        payload.get("text") or
                        payload.get("content") or
                        str(payload.get("payload", ""))
                    )
                    
                    if not isinstance(text, str):
                        text = str(text)
                    
                    # Check for error messages
                    is_trash = False
                    for pattern in ERROR_PATTERNS:
                        if pattern in text:
                            is_trash = True
                            break
                    
                    # Also check for very short content
                    if len(text.strip()) < 20:
                        is_trash = True
                    
                    if is_trash:
                        embedding_id = str(row["embedding_id"])
                        trash_ids.append(embedding_id)
                        
                        if verbose:
                            logger.info(f"Marked trash: {embedding_id[:8]}... - {text[:50]}")
                
                except Exception as e:
                    logger.debug(f"Failed to check embedding: {e}")
                    continue
            
            logger.info(f"Found {len(trash_ids)} trash embeddings")
            
            if dry_run:
                return {
                    "total": len(rows),
                    "trash_found": len(trash_ids),
                    "trash_ids": trash_ids[:20],
                    "dry_run": True,
                }
            
            # Delete in batches
            deleted = 0
            batch_size = 100
            
            for i in range(0, len(trash_ids), batch_size):
                batch = trash_ids[i:i + batch_size]
                placeholders = ",".join([f"${j+1}" for j in range(len(batch))])
                
                result = await conn.execute(
                    f"""
                    DELETE FROM semantic_memory
                    WHERE embedding_id::text IN ({placeholders})
                    """,
                    *batch,
                )
                deleted += int(result.split()[-1])
            
            return {
                "total": len(rows),
                "trash_found": len(trash_ids),
                "deleted": deleted,
                "status": "success",
            }
        
        finally:
            await conn.close()
    
    except Exception as e:
        logger.error(f"Failed to delete embeddings: {e}", exc_info=True)
        return {"error": str(e)}


async def main(dry_run: bool = False, verbose: bool = False):
    """Main function."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        logger.info("Trying to use VPS API instead...")
        # Fallback to API-based detection
        from cleanup_trash_embeddings_via_api import find_trash_embeddings_via_search
        result = await find_trash_embeddings_via_search(dry_run=dry_run, verbose=verbose)
        print(f"\nFound {result.get('trash_found', 0)} trash embeddings via API")
        print("Note: Direct DB access needed for deletion. Set DATABASE_URL in .env")
        return
    
    logger.info("Deleting trash embeddings", dry_run=dry_run)
    result = await delete_trash_embeddings(DATABASE_URL, dry_run=dry_run, verbose=verbose)
    
    if "error" in result:
        logger.error(f"Failed: {result['error']}")
        return
    
    print("\n" + "=" * 60)
    print("TRASH EMBEDDINGS DELETION")
    print("=" * 60)
    print(f"  Total embeddings: {result['total']:,}")
    print(f"  Trash found: {result['trash_found']:,}")
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - Would delete:")
        for eid in result.get("trash_ids", [])[:10]:
            print(f"    - {eid}")
    else:
        print(f"  ✅ Deleted: {result.get('deleted', 0):,} embeddings")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete trash embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

