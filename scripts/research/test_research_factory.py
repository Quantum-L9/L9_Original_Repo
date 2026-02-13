#!/usr/bin/env python3
"""
Quick test script for Quantum Research Factory endpoint.

Usage:
    # With server running:
    python scripts/test_research_factory.py

    # Or with specific URL:
    L9_BASE_URL=http://localhost:8000 python scripts/test_research_factory.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Research Factory",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "test_research_factory",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os

import httpx
import structlog


logger = structlog.get_logger(__name__)

BASE_URL = os.getenv("L9_BASE_URL", "http://localhost:8000")


async def test_research_endpoint():
    """Test the /research endpoint."""
    logger.info("\n🔬 testing quantum research factory at base url/research\n", BASE_URL=BASE_URL)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test 1: Check server status
        logger.info("1️⃣  checking server status...")
        try:
            response = await client.get(f"{BASE_URL}/")
            data = response.json()
            logger.info("   ✅ server: {data.get('status')}")
            logger.info("   ✅ version: {data.get('version')}")
            features = data.get("features", {})
            print(
                f"   ✅ Research Factory enabled: {features.get('quantum_research', False)}"
            )
        except Exception as e:
            logger.error("   ❌ failed to connect: e", e=e)
            return

        # Test 2: Execute research query
        logger.info("\n2️⃣  executing research query...")
        try:
            response = await client.post(
                f"{BASE_URL}/research",
                json={
                    "query": "What are the key components of an AI operating system?",
                    "user_id": "test_user",
                },
            )

            if response.status_code == 200:
                result = response.json()
                logger.info("   ✅ thread id: {result.get('thread_id')}")
                logger.info("   ✅ refined goal: {result.get('refined_goal', '')[:80]}...")
                logger.info("   ✅ evidence count: {result.get('evidence_count', 0)}")
                logger.info("   ✅ quality score: {result.get('quality_score', 0.0):.2f}")
                logger.info("\n   📝 summary (first 500 chars):")
                summary = result.get("summary", "No summary")
                logger.info("   {summary[:500]}...")
            elif response.status_code == 503:
                logger.info("   ⚠️  research service not initialized (503)")
                logger.info("   → check: memory_dsn environment variable set?")
                logger.info("   → check: database running?")
            else:
                logger.error("   ❌ error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error("   ❌ request failed: e", e=e)

        # Test 3: Check if Perplexity is configured
        logger.info("\n3️⃣  checking perplexity api key...")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        if perplexity_key:
            logger.info("   ✅ perplexity_api_key is set (length: {len(perplexity_key)})")
        else:
            logger.info("   ⚠️  perplexity_api_key not set - research will use mock results")
            logger.info("   → set: export perplexity_api_key='pplx-...")


async def main():
    logger.info("=" * 60")
    logger.info("   quantum research factory - activation test")
    logger.info("=" * 60")

    await test_research_endpoint()

    logger.info("\n" + "=" * 60")
    logger.info("   test complete")
    logger.info("=" * 60")


if __name__ == "__main__":
    asyncio.run(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-027",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "http-client",
        "mocking",
        "operations",
        "scripts",
        "test",
        "testing",
    ],
    "keywords": ["endpoint", "factory", "research", "test"],
    "business_value": "Utility module for test research factory",
    "last_modified": "2026-01-31T22:21:56Z",
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
