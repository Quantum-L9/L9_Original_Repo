#!/usr/bin/env python3
"""
inspect_embeddings.py - Inspect Semantic Memory Embeddings
===========================================================

Queries semantic_memory table to see what embeddings actually contain.
Helps identify if embeddings are trash from Slack glitches or other issues.

Usage:
    python3 scripts/inspect_embeddings.py [--limit N] [--agent-id AGENT] [--sample]
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Inspect Semantic Memory Embeddings",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "inspect_embeddings",
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
from typing import Any, Dict, Optional

import structlog
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv()

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


async def inspect_embeddings(
    database_url: str,
    limit: int = 50,
    agent_id: Optional[str] = None,
    sample: bool = False,
) -> Dict[str, Any]:
    """
    Inspect semantic_memory table to see what embeddings contain.

    Returns:
        Dict with statistics and sample payloads
    """
    try:
        import json as json_lib

        import asyncpg

        conn = await asyncpg.connect(database_url)
        try:
            # Get total count
            total_count = await conn.fetchval("SELECT COUNT(*) FROM semantic_memory")

            # Get count by agent_id
            agent_counts = await conn.fetch("""
                SELECT agent_id, COUNT(*) as count
                FROM semantic_memory
                GROUP BY agent_id
                ORDER BY count DESC
            """)

            # Get sample embeddings with payloads
            if agent_id:
                query = """
                    SELECT 
                        embedding_id,
                        agent_id,
                        payload::text as payload_json,
                        created_at
                    FROM semantic_memory
                    WHERE agent_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                rows = await conn.fetch(query, agent_id, limit)
            else:
                if sample:
                    # Random sample
                    query = """
                        SELECT 
                            embedding_id,
                            agent_id,
                            payload::text as payload_json,
                            created_at
                        FROM semantic_memory
                        ORDER BY RANDOM()
                        LIMIT $1
                    """
                else:
                    # Most recent
                    query = """
                        SELECT 
                            embedding_id,
                            agent_id,
                            payload::text as payload_json,
                            created_at
                        FROM semantic_memory
                        ORDER BY created_at DESC
                        LIMIT $1
                    """
                rows = await conn.fetch(query, limit)

            # Analyze payloads
            payloads = []
            payload_types = {}
            text_lengths = []
            suspicious_patterns = {
                "slack_glitch": 0,
                "empty_text": 0,
                "error_message": 0,
                "json_dump": 0,
                "very_short": 0,
            }

            for row in rows:
                try:
                    payload = (
                        json_lib.loads(row["payload_json"])
                        if row["payload_json"]
                        else {}
                    )

                    # Extract text content
                    text = (
                        payload.get("text")
                        or payload.get("content")
                        or payload.get("message")
                        or payload.get("query")
                        or str(payload.get("payload", ""))
                    )

                    # Check for suspicious patterns
                    if isinstance(text, str):
                        text_lengths.append(len(text))

                        if len(text) < 5:
                            suspicious_patterns["very_short"] += 1
                        if not text.strip():
                            suspicious_patterns["empty_text"] += 1
                        if "error" in text.lower() or "exception" in text.lower():
                            suspicious_patterns["error_message"] += 1
                        if "slack" in text.lower() and (
                            "glitch" in text.lower() or "retry" in text.lower()
                        ):
                            suspicious_patterns["slack_glitch"] += 1
                        if text.startswith("{") and text.endswith("}"):
                            suspicious_patterns["json_dump"] += 1

                    # Categorize payload type
                    payload_type = (
                        payload.get("type") or payload.get("packet_type") or "unknown"
                    )
                    payload_types[payload_type] = payload_types.get(payload_type, 0) + 1

                    payloads.append(
                        {
                            "embedding_id": str(row["embedding_id"]),
                            "agent_id": row["agent_id"],
                            "payload_type": payload_type,
                            "text_preview": str(text)[:100] if text else "",
                            "text_length": len(str(text)) if text else 0,
                            "created_at": (
                                row["created_at"].isoformat()
                                if row["created_at"]
                                else None
                            ),
                            "full_payload": payload,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to parse payload: {e}")
                    continue

            return {
                "total_embeddings": total_count,
                "agent_counts": {
                    row["agent_id"] or "null": row["count"] for row in agent_counts
                },
                "sample_size": len(payloads),
                "payload_types": payload_types,
                "text_length_stats": {
                    "min": min(text_lengths) if text_lengths else 0,
                    "max": max(text_lengths) if text_lengths else 0,
                    "avg": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
                },
                "suspicious_patterns": suspicious_patterns,
                "sample_payloads": payloads[:20],  # First 20 for inspection
            }

        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to inspect embeddings: {e}", exc_info=True)
        return {"error": str(e)}


async def main(limit: int = 50, agent_id: Optional[str] = None, sample: bool = False):
    """Main inspection function."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return

    logger.info("Inspecting semantic_memory embeddings...")
    result = await inspect_embeddings(
        DATABASE_URL, limit=limit, agent_id=agent_id, sample=sample
    )

    if "error" in result:
        logger.error(f"Inspection failed: {result['error']}")
        return

    # Print summary
    print("\n" + "=" * 60)
    print("SEMANTIC MEMORY EMBEDDINGS INSPECTION")
    print("=" * 60)
    print(f"\nTotal Embeddings: {result['total_embeddings']:,}")

    print("\nEmbeddings by Agent:")
    for agent, count in sorted(
        result["agent_counts"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {agent or '(null)':20} {count:>8,}")

    print(f"\nPayload Types (sample of {result['sample_size']}):")
    for ptype, count in sorted(
        result["payload_types"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {ptype:30} {count:>5}")

    print("\nText Length Statistics:")
    stats = result["text_length_stats"]
    print(f"  Min:  {stats['min']:>6} chars")
    print(f"  Max:  {stats['max']:>6} chars")
    print(f"  Avg:  {stats['avg']:>6.1f} chars")

    print("\nSuspicious Patterns Detected:")
    for pattern, count in result["suspicious_patterns"].items():
        if count > 0:
            print(f"  {pattern:20} {count:>5}")

    print("\n" + "-" * 60)
    print("SAMPLE PAYLOADS (first 20):")
    print("-" * 60)
    for i, payload in enumerate(result["sample_payloads"][:20], 1):
        print(f"\n[{i}] Embedding: {payload['embedding_id'][:8]}...")
        print(f"    Agent: {payload['agent_id']}")
        print(f"    Type: {payload['payload_type']}")
        print(f"    Text Length: {payload['text_length']} chars")
        print(f"    Created: {payload['created_at']}")
        print(f"    Preview: {payload['text_preview'][:150]}")
        if payload["text_length"] > 0 and payload["text_length"] < 200:
            print(f"    Full Text: {payload['text_preview']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect semantic memory embeddings")
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of samples to inspect"
    )
    parser.add_argument("--agent-id", type=str, help="Filter by agent_id")
    parser.add_argument(
        "--sample", action="store_true", help="Random sample instead of most recent"
    )

    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, agent_id=args.agent_id, sample=args.sample))

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "cli",
        "debugging",
        "filesystem",
        "logging",
        "memory-substrate",
        "messaging",
        "operations",
        "postgres",
        "serialization",
    ],
    "keywords": ["embeddings", "inspect", "memory", "semantic"],
    "business_value": "Utility module for inspect embeddings",
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
