#!/usr/bin/env python3
"""
cleanup_trash_embeddings_via_api.py - Clean Up Trash Embeddings via VPS API
============================================================================

Deletes embeddings containing error messages via VPS memory API.
Safer than direct DB access.

Usage:
    python3 scripts/cleanup_trash_embeddings_via_api.py [--dry-run] [--verbose]
"""

import os
import sys
import re
import asyncio
import httpx
import structlog
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

# Patterns that indicate trash embeddings
TRASH_PATTERNS = [
    r"Sorry, I encountered (a temporary error|an error)",
    r"Sorry, I encountered a temporary error\. Please try again\.",
    r"Sorry, I encountered an error processing your command\.",
    r"No response generated\.",
    r"This message has already been processed\.",
]


def is_trash_embedding(payload: dict) -> bool:
    """Check if embedding payload indicates trash content."""
    text = (
        payload.get("_text") or
        payload.get("text") or
        payload.get("content") or
        str(payload.get("payload", ""))
    )
    
    if not isinstance(text, str):
        text = str(text)
    
    text = text.strip()
    
    # Check against trash patterns
    for pattern in TRASH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Very short content
    if len(text) < 20:
        return True
    
    return False


async def find_trash_embeddings_via_search(
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Find trash embeddings by doing semantic searches."""
    if not API_KEY:
        logger.error("L9_EXECUTOR_API_KEY not set")
        return {"error": "API key not set"}
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Search for error messages to find trash embeddings
    search_queries = [
        "Sorry, I encountered a temporary error",
        "Sorry, I encountered an error",
        "No response generated",
    ]
    
    trash_embedding_ids = []
    checked_count = 0
    
    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        for query in search_queries:
            try:
                response = await client.post(
                    f"{VPS_URL}/api/v1/memory/semantic/search",
                    headers=headers,
                    json={
                        "query": query,
                        "top_k": 100,  # Get many results
                        "min_score": 0.1,  # Very low threshold to catch all
                    },
                )
                
                if response.status_code == 200:
                    result = response.json()
                    hits = result.get("hits", [])
                    checked_count += len(hits)
                    
                    for hit in hits:
                        payload = hit.get("payload", {})
                        embedding_id = hit.get("embedding_id")
                        
                        if is_trash_embedding(payload) and embedding_id:
                            if embedding_id not in trash_embedding_ids:
                                trash_embedding_ids.append(embedding_id)
                                
                                if verbose:
                                    text = payload.get("_text") or payload.get("text", "")[:50]
                                    logger.info(f"Found trash: {embedding_id} - {text}")
            
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
    
    logger.info(f"Found {len(trash_embedding_ids)} trash embeddings")
    
    if dry_run:
        return {
            "checked": checked_count,
            "trash_found": len(trash_embedding_ids),
            "trash_ids": trash_embedding_ids[:20],  # Sample
            "dry_run": True,
        }
    
    # Delete via API (if endpoint exists) or direct DB
    # For now, return IDs for manual deletion or use direct DB script
    return {
        "checked": checked_count,
        "trash_found": len(trash_embedding_ids),
        "trash_ids": trash_embedding_ids,
        "status": "found",
    }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main cleanup function."""
    logger.info("Finding trash embeddings via API", dry_run=dry_run)
    
    result = await find_trash_embeddings_via_search(dry_run=dry_run, verbose=verbose)
    
    if "error" in result:
        logger.error(f"Failed: {result['error']}")
        return
    
    print("\n" + "=" * 60)
    print("TRASH EMBEDDINGS DETECTION (via API)")
    print("=" * 60)
    print(f"  Embeddings checked: {result['checked']}")
    print(f"  Trash embeddings found: {result['trash_found']}")
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - Sample trash IDs:")
        for eid in result.get("trash_ids", [])[:10]:
            print(f"    - {eid}")
        print("\n  Run without --dry-run to get full list for deletion")
    else:
        print(f"\n  Found {len(result.get('trash_ids', []))} trash embedding IDs")
        print("  Note: Use cleanup_trash_embeddings.py with DATABASE_URL for deletion")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find trash embeddings via API")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

