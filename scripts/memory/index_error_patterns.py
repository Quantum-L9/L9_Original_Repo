#!/usr/bin/env python3
"""
index_error_patterns.py - Index Error Patterns to Memory Graph
===============================================================

Queries packet_store for packets with kind=FAILURE, extracts error_type, error_message, fix_applied,
and creates knowledge facts (subject=error_type, predicate=fixed_by, object=solution) plus semantic embeddings.

Created: 2026-01-09
Version: 1.0.0

Usage:
    python3 scripts/index_error_patterns.py [--dry-run] [--verbose]

Features:
- Queries packet_store for FAILURE packets
- Extracts error patterns (error_type, error_message, fix_applied)
- Creates knowledge facts for error-solution mappings
- Creates semantic embeddings for error context
- Uses memory substrate APIs
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import structlog
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv()

logger = structlog.get_logger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


def extract_error_type(error_message: str) -> str:
    """Extract error type from error message."""
    # Common error patterns
    patterns = [
        (r'(\w+Error)', 'Python exception'),
        (r'(\w+Exception)', 'Python exception'),
        (r'HTTP (\d+)', 'HTTP error'),
        (r'ConnectionError', 'Connection error'),
        (r'TimeoutError', 'Timeout error'),
        (r'ValueError', 'Value error'),
        (r'KeyError', 'Key error'),
        (r'AttributeError', 'Attribute error'),
        (r'ImportError', 'Import error'),
        (r'TypeError', 'Type error'),
    ]
    
    for pattern, error_type in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else error_type
    
    # Default: use first word or "UnknownError"
    words = error_message.split()
    if words:
        return words[0].replace(':', '').replace(',', '')
    return "UnknownError"


async def query_failure_packets(database_url: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Query packet_store for packets with kind=FAILURE.
    
    Returns:
        List of dicts with packet_id, error_message, error_type, payload, metadata
    """
    try:
        import asyncpg
        import json as json_lib
        
        conn = await asyncpg.connect(database_url)
        try:
            rows = await conn.fetch("""
                SELECT 
                    packet_id,
                    envelope::jsonb->>'payload' as payload_json,
                    envelope::jsonb->>'metadata' as metadata_json,
                    created_at
                FROM packet_store
                WHERE envelope::jsonb->>'kind' = 'FAILURE'
                   OR envelope::jsonb->>'packet_type' LIKE '%error%'
                   OR envelope::jsonb->>'packet_type' LIKE '%failure%'
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            
            failures = []
            for row in rows:
                try:
                    payload = json_lib.loads(row["payload_json"]) if row["payload_json"] else {}
                    metadata = json_lib.loads(row["metadata_json"]) if row["metadata_json"] else {}
                    
                    error_message = (
                        payload.get("error_message") or
                        payload.get("error") or
                        payload.get("message") or
                        str(payload.get("text", ""))
                    )
                    
                    if not error_message or len(error_message) < 10:
                        continue
                    
                    error_type = extract_error_type(error_message)
                    
                    # Try to extract fix/solution from payload
                    fix_applied = (
                        payload.get("fix") or
                        payload.get("solution") or
                        payload.get("fix_applied") or
                        payload.get("recovery_action") or
                        ""
                    )
                    
                    failures.append({
                        "packet_id": str(row["packet_id"]),
                        "error_message": error_message,
                        "error_type": error_type,
                        "fix_applied": fix_applied,
                        "payload": payload,
                        "metadata": metadata,
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse packet {row['packet_id']}: {e}")
                    continue
            
            return failures
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to query failure packets: {e}", exc_info=True)
        return []


async def index_error_patterns(
    failures: List[Dict[str, Any]],
    substrate_service: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Index error patterns to memory substrate.
    
    Creates:
    - Knowledge facts (subject=error_type, predicate=fixed_by, object=solution)
    - Semantic embeddings for error context
    """
    if dry_run:
        logger.info(f"DRY RUN - would index {len(failures)} error patterns")
        return {"errors_indexed": len(failures), "dry_run": True}
    
    facts_created = 0
    embeddings_created = 0
    errors = []
    
    for failure in failures:
        try:
            error_type = failure["error_type"]
            error_message = failure["error_message"]
            fix_applied = failure.get("fix_applied", "")
            packet_id = failure["packet_id"]
            
            # Create knowledge fact for error-solution mapping
            if fix_applied and len(fix_applied) > 10:
                try:
                    await substrate_service._repository.insert_knowledge_fact(
                        subject=error_type,
                        predicate="fixed_by",
                        object_value={
                            "solution": fix_applied,
                            "error_message": error_message[:200],
                            "source_packet": packet_id,
                        },
                        confidence=0.85,
                        source_packet=packet_id if packet_id else None,
                    )
                    facts_created += 1
                except Exception as e:
                    logger.debug(f"Failed to create fact for {error_type}: {e}")
            
            # Create semantic embedding for error context
            error_context = f"""
Error Type: {error_type}
Error Message: {error_message}
Fix Applied: {fix_applied if fix_applied else "No fix recorded"}
"""
            try:
                embedding_id = await substrate_service.embed_text(
                    text=error_context,
                    payload={
                        "error_type": error_type,
                        "error_message": error_message[:200],
                        "has_fix": bool(fix_applied),
                        "type": "error_pattern",
                        "source_packet": packet_id,
                    },
                    agent_id="system",
                )
                embeddings_created += 1
            except Exception as e:
                logger.debug(f"Failed to create embedding for {error_type}: {e}")
        
        except Exception as e:
            errors.append(f"Error {failure.get('packet_id', 'unknown')}: {str(e)}")
            logger.debug(f"Failed to index error pattern: {e}")
    
    return {
        "errors_indexed": len(failures),
        "facts_created": facts_created,
        "embeddings_created": embeddings_created,
        "errors": errors,
        "status": "success" if not errors else "partial",
    }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main indexing function."""
    logger.info("Starting error patterns indexing", dry_run=dry_run)
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return
    
    # Query failure packets
    logger.info("Querying packet_store for FAILURE packets...")
    failures = await query_failure_packets(DATABASE_URL, limit=1000)
    logger.info(f"Found {len(failures)} failure packets")
    
    if not failures:
        logger.warning("No failure packets found")
        return
    
    if verbose:
        logger.info("Sample error patterns:")
        for failure in failures[:5]:
            logger.info(
                f"  {failure['error_type']}: {failure['error_message'][:50]}..."
            )
    
    # Initialize memory substrate service
    try:
        from memory.substrate_service import init_service, close_service
        
        service = await init_service(DATABASE_URL)
        logger.info("Memory substrate service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory substrate: {e}", exc_info=True)
        return
    
    try:
        # Index error patterns
        result = await index_error_patterns(failures, service, dry_run=dry_run)
        
        # Summary
        logger.info("=" * 60)
        logger.info("ERROR PATTERNS INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Failure packets found: {len(failures)}")
        logger.info(f"  Errors indexed: {result.get('errors_indexed', 0)}")
        logger.info(f"  Facts created: {result.get('facts_created', 0)}")
        logger.info(f"  Embeddings created: {result.get('embeddings_created', 0)}")
        if result.get("errors"):
            logger.warning(f"  Errors: {len(result['errors'])}")
            for error in result["errors"][:5]:
                logger.warning(f"    - {error}")
        logger.info("=" * 60)
        
    finally:
        await close_service()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index error patterns to memory graph")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

