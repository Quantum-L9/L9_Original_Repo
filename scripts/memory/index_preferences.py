#!/usr/bin/env python3
"""
index_preferences.py - Index User Preferences to Memory Graph
=============================================================

Queries packet_store for packets with kind=preference, extracts from Slack user corrections
and stated preferences, creates knowledge facts (subject=Igor, predicate=prefers, object=pattern),
and creates semantic embeddings for preference context.

Created: 2026-01-09
Version: 1.0.0

Usage:
    python3 scripts/index_preferences.py [--dry-run] [--verbose]

Features:
- Queries packet_store for preference packets
- Extracts preferences from Slack conversations (already indexed by slack_ingest.py)
- Creates knowledge facts for user preferences
- Creates semantic embeddings for preference context
- Uses memory substrate APIs
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Index User Preferences to Memory Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "index_preferences",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

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


async def query_preference_packets(
    database_url: str, limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Query packet_store for packets with kind=preference.

    Also queries knowledge_facts for preferences already extracted from Slack.

    Returns:
        List of dicts with preference data
    """
    try:
        import json as json_lib

        import asyncpg

        conn = await asyncpg.connect(database_url)
        try:
            # Query preference packets
            packet_rows = await conn.fetch(
                """
                SELECT 
                    packet_id,
                    envelope::jsonb->>'payload' as payload_json,
                    envelope::jsonb->>'metadata' as metadata_json,
                    created_at
                FROM packet_store
                WHERE envelope::jsonb->>'kind' = 'preference'
                   OR envelope::jsonb->>'packet_type' LIKE '%preference%'
                ORDER BY created_at DESC
                LIMIT $1
            """,
                limit,
            )

            preferences = []
            for row in packet_rows:
                try:
                    payload = (
                        json_lib.loads(row["payload_json"])
                        if row["payload_json"]
                        else {}
                    )
                    metadata = (
                        json_lib.loads(row["metadata_json"])
                        if row["metadata_json"]
                        else {}
                    )

                    preference_text = (
                        payload.get("preference")
                        or payload.get("text")
                        or payload.get("content")
                        or payload.get("message")
                        or ""
                    )

                    if not preference_text or len(preference_text) < 10:
                        continue

                    user_id = metadata.get("agent") or payload.get("user_id") or "Igor"

                    preferences.append(
                        {
                            "packet_id": str(row["packet_id"]),
                            "user_id": user_id,
                            "preference_text": preference_text,
                            "payload": payload,
                            "metadata": metadata,
                            "created_at": (
                                row["created_at"].isoformat()
                                if row["created_at"]
                                else None
                            ),
                            "source": "preference_packet",
                        }
                    )
                except Exception as e:
                    logger.debug(
                        f"Failed to parse preference packet {row['packet_id']}: {e}"
                    )
                    continue

            # Also query knowledge_facts for preferences already extracted
            fact_rows = await conn.fetch(
                """
                SELECT 
                    fact_id,
                    subject,
                    predicate,
                    object::text as object_json,
                    confidence,
                    source_packet,
                    created_at
                FROM knowledge_facts
                WHERE predicate = 'prefers' OR predicate = 'corrects'
                ORDER BY created_at DESC
                LIMIT $1
            """,
                limit,
            )

            for row in fact_rows:
                try:
                    object_data = (
                        json_lib.loads(row["object_json"]) if row["object_json"] else {}
                    )
                    preference_text = (
                        object_data.get("preference")
                        or object_data.get("correction")
                        or str(object_data)
                    )

                    if len(preference_text) < 10:
                        continue

                    preferences.append(
                        {
                            "packet_id": (
                                str(row["source_packet"])
                                if row["source_packet"]
                                else None
                            ),
                            "user_id": row["subject"],
                            "preference_text": preference_text,
                            "payload": object_data,
                            "metadata": {},
                            "created_at": (
                                row["created_at"].isoformat()
                                if row["created_at"]
                                else None
                            ),
                            "source": "knowledge_fact",
                            "fact_id": str(row["fact_id"]),
                        }
                    )
                except Exception as e:
                    logger.debug(
                        f"Failed to parse preference fact {row['fact_id']}: {e}"
                    )
                    continue

            # Deduplicate by preference_text (keep most recent)
            seen = {}
            for pref in preferences:
                key = pref["preference_text"][:100]  # Use first 100 chars as key
                if key not in seen or pref["created_at"] > seen[key]["created_at"]:
                    seen[key] = pref

            return list(seen.values())

        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to query preference packets: {e}", exc_info=True)
        return []


async def index_preferences(
    preferences: List[Dict[str, Any]],
    substrate_service: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Index user preferences to memory substrate.

    Creates:
    - Knowledge facts (subject=user_id, predicate=prefers, object=pattern)
    - Semantic embeddings for preference context
    """
    if dry_run:
        logger.info(f"DRY RUN - would index {len(preferences)} preferences")
        return {"preferences_indexed": len(preferences), "dry_run": True}

    facts_created = 0
    embeddings_created = 0
    errors = []

    for preference in preferences:
        try:
            user_id = preference["user_id"]
            preference_text = preference["preference_text"]
            packet_id = preference.get("packet_id")

            # Create knowledge fact (if not already exists from slack_ingest)
            if preference.get("source") == "preference_packet":
                try:
                    await substrate_service._repository.insert_knowledge_fact(
                        subject=user_id,
                        predicate="prefers",
                        object_value={
                            "preference": preference_text,
                            "source": "preference_packet",
                            "created_at": preference.get("created_at"),
                        },
                        confidence=0.9,
                        source_packet=packet_id if packet_id else None,
                    )
                    facts_created += 1
                except Exception as e:
                    logger.debug(f"Failed to create preference fact: {e}")

            # Create semantic embedding for preference context
            preference_context = f"""
User Preference: {user_id}
Preference: {preference_text}
Source: {preference.get("source", "unknown")}
"""
            try:
                await substrate_service.embed_text(
                    text=preference_context,
                    payload={
                        "user_id": user_id,
                        "preference": preference_text[:200],
                        "type": "user_preference",
                        "source": preference.get("source"),
                        "source_packet": packet_id,
                    },
                    agent_id=user_id,
                )
                embeddings_created += 1
            except Exception as e:
                logger.debug(f"Failed to create preference embedding: {e}")

        except Exception as e:
            errors.append(
                f"Preference {preference.get('packet_id', 'unknown')}: {str(e)}"
            )
            logger.debug(f"Failed to index preference: {e}")

    return {
        "preferences_indexed": len(preferences),
        "facts_created": facts_created,
        "embeddings_created": embeddings_created,
        "errors": errors,
        "status": "success" if not errors else "partial",
    }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main indexing function."""
    logger.info("Starting user preferences indexing", dry_run=dry_run)

    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return

    # Query preference packets and facts
    logger.info("Querying packet_store and knowledge_facts for preferences...")
    preferences = await query_preference_packets(DATABASE_URL, limit=1000)
    logger.info(f"Found {len(preferences)} preferences")

    if not preferences:
        logger.warning("No preferences found")
        return

    if verbose:
        logger.info("Sample preferences:")
        for pref in preferences[:5]:
            logger.info(f"  {pref['user_id']}: {pref['preference_text'][:50]}...")

    # Initialize memory substrate service
    try:
        from memory.substrate_service import close_service, init_service

        service = await init_service(DATABASE_URL)
        logger.info("Memory substrate service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory substrate: {e}", exc_info=True)
        return

    try:
        # Index preferences
        result = await index_preferences(preferences, service, dry_run=dry_run)

        # Summary
        logger.info("=" * 60)
        logger.info("USER PREFERENCES INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Preferences found: {len(preferences)}")
        logger.info(f"  Preferences indexed: {result.get('preferences_indexed', 0)}")
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

    parser = argparse.ArgumentParser(
        description="Index user preferences to memory graph"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
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
    "dependencies": ["memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "cli",
        "debugging",
        "filesystem",
        "logging",
        "memory-substrate",
        "messaging",
        "operations",
        "postgres",
    ],
    "keywords": [
        "graph",
        "index",
        "memory",
        "packets",
        "preference",
        "preferences",
        "query",
        "user",
    ],
    "business_value": "Utility module for index preferences",
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
