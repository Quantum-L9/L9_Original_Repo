#!/usr/bin/env python3
"""
cleanup_trash_embeddings.py - Clean Up Trash Embeddings
========================================================

Deletes embeddings containing error messages, empty text, JSON dumps, and other low-value content.

Usage:
    python3 scripts/cleanup_trash_embeddings.py [--dry-run] [--verbose]
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Clean Up Trash Embeddings",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "cleanup_trash_embeddings",
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

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any
import asyncio
import structlog
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")

# Patterns that indicate trash embeddings
TRASH_PATTERNS = [
    # Error messages
    r"Sorry, I encountered (a temporary error|an error)",
    r"Sorry, I encountered a temporary error\. Please try again\.",
    r"Sorry, I encountered an error processing your command\.",
    r"No response generated\.",
    r"This message has already been processed\.",
    r"L9 agent executor not available",
    r"Mac agent is not available",
    # Very short content (likely noise)
    r"^.{0,20}$",  # Less than 20 chars
    # JSON dumps (unstructured data)
    r"^\{.*\}$",  # Starts and ends with braces
    # Empty or whitespace only
    r"^\s*$",
]

def is_trash_embedding(payload: Dict[str, Any]) -> bool:
    """
    Check if an embedding payload indicates trash content.
    
    Returns:
        True if embedding should be deleted
    """
    # Extract text content
    text = (
        payload.get("_text") or
        payload.get("text") or
        payload.get("content") or
        payload.get("message") or
        str(payload.get("payload", ""))
    )
    
    if not isinstance(text, str):
        text = str(text)
    
    text = text.strip()
    
    # Check against trash patterns
    for pattern in TRASH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True
    
    # Check for very short content
    if len(text) < 20:
        return True
    
    # Check if it's a JSON dump (starts with { and ends with })
    if text.startswith("{") and text.endswith("}") and len(text) < 500:
        try:
            json.loads(text)
            # If it parses as JSON and is short, it's likely a dump
            return True
        except:
            pass
    
    return False

async def cleanup_trash_embeddings(
    database_url: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Find and delete trash embeddings from semantic_memory table.
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        import asyncpg
        import json as json_lib
        
        conn = await asyncpg.connect(database_url)
        try:
            # Get all embeddings with payloads
            rows = await conn.fetch("""
                SELECT 
                    embedding_id,
                    payload::text as payload_json,
                    agent_id,
                    created_at
                FROM semantic_memory
                ORDER BY created_at DESC
            """)
            
            logger.info(f"Scanning {len(rows)} embeddings...")
            
            trash_ids = []
            trash_reasons = {}
            
            for row in rows:
                try:
                    payload = json_lib.loads(row["payload_json"]) if row["payload_json"] else {}
                    
                    if is_trash_embedding(payload):
                        embedding_id = str(row["embedding_id"])
                        trash_ids.append(embedding_id)
                        
                        # Determine reason
                        text = (
                            payload.get("_text") or
                            payload.get("text") or
                            str(payload)[:100]
                        )
                        
                        if "Sorry, I encountered" in str(text):
                            reason = "error_message"
                        elif len(str(text)) < 20:
                            reason = "too_short"
                        elif str(text).startswith("{") and str(text).endswith("}"):
                            reason = "json_dump"
                        else:
                            reason = "trash_pattern"
                        
                        trash_reasons[embedding_id] = reason
                        
                        if verbose:
                            logger.info(
                                f"Marked as trash: {embedding_id[:8]}... "
                                f"({reason}) - {str(text)[:50]}"
                            )
                
                except Exception as e:
                    logger.debug(f"Failed to check embedding {row['embedding_id']}: {e}")
                    continue
            
            logger.info(f"Found {len(trash_ids)} trash embeddings to delete")
            
            if dry_run:
                logger.info("DRY RUN - would delete:")
                for eid in trash_ids[:10]:
                    logger.info(f"  - {eid} ({trash_reasons.get(eid, 'unknown')})")
                return {
                    "total_scanned": len(rows),
                    "trash_found": len(trash_ids),
                    "dry_run": True,
                }
            
            # Delete trash embeddings
            if trash_ids:
                # Delete in batches of 100
                batch_size = 100
                deleted_count = 0
                
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
                    deleted_count += int(result.split()[-1])
                
                logger.info(f"Deleted {deleted_count} trash embeddings")
            
            # Get statistics by reason
            reason_counts = {}
            for reason in trash_reasons.values():
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            return {
                "total_scanned": len(rows),
                "trash_found": len(trash_ids),
                "deleted": deleted_count if not dry_run else 0,
                "reason_counts": reason_counts,
                "status": "success",
            }
            
        finally:
            await conn.close()
    
    except Exception as e:
        logger.error(f"Failed to cleanup embeddings: {e}", exc_info=True)
        return {"error": str(e), "status": "error"}

async def main(dry_run: bool = False, verbose: bool = False):
    """Main cleanup function."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return
    
    logger.info("Starting trash embeddings cleanup", dry_run=dry_run)
    
    result = await cleanup_trash_embeddings(DATABASE_URL, dry_run=dry_run, verbose=verbose)
    
    if "error" in result:
        logger.error(f"Cleanup failed: {result['error']}")
        return
    
    # Print summary
    print("\n" + "=" * 60)
    print("TRASH EMBEDDINGS CLEANUP SUMMARY")
    print("=" * 60)
    print(f"  Total embeddings scanned: {result['total_scanned']:,}")
    print(f"  Trash embeddings found: {result['trash_found']:,}")
    
    if result.get("reason_counts"):
        print("\n  Breakdown by reason:")
        for reason, count in sorted(result["reason_counts"].items(), key=lambda x: x[1], reverse=True):
            print(f"    {reason:20} {count:>6}")
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - No embeddings deleted")
    else:
        print(f"\n  ✅ Deleted: {result.get('deleted', 0):,} embeddings")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up trash embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no deletes)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "batch-processing", "cli", "debugging", "filesystem", "logging", "memory-substrate", "messaging", "operations", "postgres"],
    "keywords": ["clean", "cleanup", "embedding", "embeddings", "trash"],
    "business_value": "Utility module for cleanup trash embeddings",
    "last_modified": "2026-01-14T15:03:00Z",
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
