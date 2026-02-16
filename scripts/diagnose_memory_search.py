#!/usr/bin/env python3
"""
Diagnose Memory Search Issue
============================

Runs diagnostic queries to understand why search returns empty despite successful writes.

Usage:
    python3 scripts/diagnose_memory_search.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Diagnose Memory Search",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "diagnose_memory_search",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import json
import os
import ssl
import urllib.request

import structlog

# SSL context for self-signed cert

logger = structlog.get_logger(__name__)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

L9_API_URL = os.getenv("L9_API_URL", "https://157.180.73.53:9001")
L9_EXECUTOR_API_KEY = os.getenv("L9_EXECUTOR_API_KEY", "")


def mcp_call(tool_name: str, arguments: dict) -> dict:
    """Call MCP tool."""
    url = f"{L9_API_URL}/mcp/call"
    headers = {
        "Authorization": f"Bearer {L9_EXECUTOR_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"tool_name": tool_name, "arguments": arguments}
    req = urllib.request.Request(  # noqa: S310 — URL from trusted config
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:  # noqa: S310 — URL from trusted config
            result = json.loads(response.read().decode())
            if result.get("status") == "success":
                return result.get("result", {})
            return {"error": result.get("detail", "MCP call failed")}
    except Exception as e:
        return {"error": str(e)}


def main():
    """
    Performs memory search diagnostics to identify issues with empty search results despite successful writes.



    Raises:
        Exception: If any errors occur during diagnostic steps.
    """
    logger.info("=" * 60)
    logger.info("memory search diagnostic")
    logger.info("=" * 60)

    # Step 1: Check stats
    logger.info("\n1. memory stats:")
    stats = mcp_call("get_memory_stats", {})
    logger.info("output", value=json.dumps(stats, indent=2))

    # Step 2: Write a unique test memory
    test_content = "DIAG_TEST_12345_UNIQUE_MARKER"
    logger.info("\n2. writing test memory: test content", test_content=test_content)
    write_result = mcp_call(
        "save_memory",
        {
            "content": test_content,
            "kind": "note",
            "scope": "developer",
            "duration": "medium",
            "tags": ["diagnostic", "test"],
            "importance": 1.0,
        },
    )
    logger.info("write result:")
    logger.info("output", value=json.dumps(write_result, indent=2))

    if "error" in write_result:
        logger.error("\n❌ write failed - cannot continue diagnostic")
        return

    packet_id = write_result.get("packet_id")
    written_tables = write_result.get("written_tables", [])
    logger.info("\n   packet id: packet id", packet_id=packet_id)
    logger.info("   written tables: written tables", written_tables=written_tables)
    logger.info("   semantic_memory written: {'semantic_memory' in written_tables}")

    # Step 3: Search for it with various thresholds
    logger.info("\n3. searching for test memory:")

    for threshold in [0.0, 0.3, 0.5, 0.7]:
        logger.info("\n   threshold: threshold", threshold=threshold)
        search_result = mcp_call(
            "search_memory",
            {
                "query": test_content,
                "scopes": ["developer", "global"],
                "top_k": 10,
                "threshold": threshold,
                "duration": "all",
            },
        )
        results = search_result.get("results", [])
        logger.info("   results count: {len(results)}")
        if results:
            for r in results[:3]:
                print(
                    f"   - {r.get('content', '')[:50]}... (similarity: {r.get('similarity', 'N/A')})"
                )
        else:
            logger.info("   (no results)")

    # Step 4: Check stats after write
    logger.info("\n4. stats after write:")
    stats_after = mcp_call("get_memory_stats", {})
    logger.info("output", value=json.dumps(stats_after, indent=2))

    # Step 5: Summary
    logger.info("\n" + "=" * 60)
    logger.info("diagnosis summary")
    logger.info("=" * 60)

    stats_total_before = stats.get("total_count", 0) if isinstance(stats, dict) else 0
    stats_total_after = (
        stats_after.get("total_count", 0) if isinstance(stats_after, dict) else 0
    )

    logger.info(
        "stats total before write: stats total before",
        stats_total_before=stats_total_before,
    )
    logger.info(
        "stats total after write: stats total after",
        stats_total_after=stats_total_after,
    )
    logger.info("stats increased: {stats_total_after > stats_total_before}")
    logger.info(
        "semantic_memory in written_tables: {'semantic_memory' in written_tables}"
    )
    print(
        f"Search found results: {len(search_result.get('results', [])) > 0 if isinstance(search_result, dict) else False}"
    )

    if "semantic_memory" in written_tables and stats_total_after == stats_total_before:
        logger.info("\n⚠️  issue: semantic_memory written but stats didn't increase")
        print(
            "   Possible cause: Stats query filters by packet_type LIKE 'memory_write_%'"
        )
        logger.info(
            "   but writes use packet_type 'memory.{kind}' (e.g., 'memory.note')"
        )
        logger.info("   fix: update stats query or update write packet_type format")


if __name__ == "__main__":
    if not L9_EXECUTOR_API_KEY:
        logger.error("error: l9_executor_api_key not set")
        logger.info("run: export l9_executor_api_key=your_key")
    else:
        main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "cli", "operations", "scripts", "serialization", "testing"],
    "keywords": ["diagnose", "mcp", "memory", "search"],
    "business_value": "Utility module for diagnose memory search",
    "last_modified": "2026-01-17T23:47:56Z",
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
