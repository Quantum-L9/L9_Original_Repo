#!/usr/bin/env python3
"""
check_embeddings_via_api.py - Check Embeddings via VPS API
==========================================================

Uses VPS memory API to inspect what embeddings contain.
Safer than direct DB access.

Usage:
    python3 scripts/check_embeddings_via_api.py [--limit N]
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Embeddings via VPS API",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "check_embeddings_via_api",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os
import sys
from pathlib import Path

import httpx
import structlog
from dotenv import load_dotenv

from core.decorators import must_stay_async

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

logger = structlog.get_logger(__name__)

VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")


@must_stay_async("callers use await")
async def check_embeddings_via_search(limit: int = 20):
    """Check embeddings by doing semantic searches and inspecting results."""
    if not API_KEY:
        logger.error("L9_EXECUTOR_API_KEY not set")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # Test queries to see what comes back
    test_queries = [
        "slack message",
        "error",
        "test",
        "preference",
        "decision",
    ]

    logger.info("\n" + "=" * 60)
    logger.info("checking embeddings via semantic search")
    logger.info("=" * 60)

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:  # noqa: S501 — internal VPS service, cert validation not required
        for query in test_queries:
            logger.info("\n🔍 query: 'query'", query=query)
            logger.info("-" * 60)

            try:
                response = await client.post(
                    f"{VPS_URL}/api/v1/memory/semantic/search",
                    headers=headers,
                    json={
                        "query": query,
                        "top_k": 5,
                        "min_score": 0.3,  # Lower threshold to see more
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    hits = result.get("hits", [])
                    logger.info("  found {len(hits)} results")

                    for i, hit in enumerate(hits[:3], 1):
                        payload = hit.get("payload", {})
                        score = hit.get("score", 0)
                        text = (
                            payload.get("_text")
                            or payload.get("text")
                            or payload.get("content")
                            or str(payload)[:200]
                        )

                        logger.info("\n  [i] score: {score:.3f}", i=i)
                        logger.info("      type: {payload.get('type', 'unknown')}")
                        logger.info("      agent: {payload.get('agent_id', 'unknown')}")
                        logger.info("      text: {text[:150]}...")
                else:
                    logger.error(
                        "  ❌ error: {response.status_code} - {response.text[:200]}"
                    )

            except Exception as e:
                logger.info("  ❌ exception: e", e=e)

    logger.info("\n" + "=" * 60)
    logger.info("summary")
    logger.info("=" * 60)
    logger.info("\nif you see:")
    logger.error("  - empty/error messages → trash embeddings from slack glitch")
    logger.info("  - meaningful content → embeddings are valid")
    logger.info("  - very short text (< 20 chars) → likely noise")
    logger.info("  - json dumps → unstructured data got embedded")
    logger.info("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check embeddings via VPS API")
    parser.add_argument(
        "--limit", type=int, default=20, help="Number of results per query"
    )

    args = parser.parse_args()

    asyncio.run(check_embeddings_via_search(limit=args.limit))

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
        "api",
        "async",
        "auth",
        "cli",
        "filesystem",
        "http-client",
        "logging",
        "memory-substrate",
        "messaging",
        "operations",
    ],
    "keywords": ["api", "check", "embeddings", "search", "via", "vps"],
    "business_value": "Utility module for check embeddings via api",
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
