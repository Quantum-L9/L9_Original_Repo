#!/usr/bin/env python3
"""
Diagnose Memory Search Issue
============================

Runs diagnostic queries to understand why search returns empty despite successful writes.

Usage:
    python3 scripts/diagnose_memory_search.py
"""

import os
import json
import urllib.request
import ssl

# SSL context for self-signed cert
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
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            result = json.loads(response.read().decode())
            if result.get("status") == "success":
                return result.get("result", {})
            return {"error": result.get("detail", "MCP call failed")}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("MEMORY SEARCH DIAGNOSTIC")
    print("=" * 60)

    # Step 1: Check stats
    print("\n1. MEMORY STATS:")
    stats = mcp_call("get_memory_stats", {})
    print(json.dumps(stats, indent=2))

    # Step 2: Write a unique test memory
    test_content = "DIAG_TEST_12345_UNIQUE_MARKER"
    print(f"\n2. WRITING TEST MEMORY: {test_content}")
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
    print("Write result:")
    print(json.dumps(write_result, indent=2))

    if "error" in write_result:
        print("\n❌ Write failed - cannot continue diagnostic")
        return

    packet_id = write_result.get("packet_id")
    written_tables = write_result.get("written_tables", [])
    print(f"\n   packet_id: {packet_id}")
    print(f"   written_tables: {written_tables}")
    print(f"   semantic_memory written: {'semantic_memory' in written_tables}")

    # Step 3: Search for it with various thresholds
    print("\n3. SEARCHING FOR TEST MEMORY:")

    for threshold in [0.0, 0.3, 0.5, 0.7]:
        print(f"\n   Threshold: {threshold}")
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
        print(f"   Results count: {len(results)}")
        if results:
            for r in results[:3]:
                print(
                    f"   - {r.get('content', '')[:50]}... (similarity: {r.get('similarity', 'N/A')})"
                )
        else:
            print("   (no results)")

    # Step 4: Check stats after write
    print("\n4. STATS AFTER WRITE:")
    stats_after = mcp_call("get_memory_stats", {})
    print(json.dumps(stats_after, indent=2))

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)

    stats_total_before = stats.get("total_count", 0) if isinstance(stats, dict) else 0
    stats_total_after = (
        stats_after.get("total_count", 0) if isinstance(stats_after, dict) else 0
    )

    print(f"Stats total before write: {stats_total_before}")
    print(f"Stats total after write: {stats_total_after}")
    print(f"Stats increased: {stats_total_after > stats_total_before}")
    print(f"semantic_memory in written_tables: {'semantic_memory' in written_tables}")
    print(
        f"Search found results: {len(search_result.get('results', [])) > 0 if isinstance(search_result, dict) else False}"
    )

    if "semantic_memory" in written_tables and stats_total_after == stats_total_before:
        print("\n⚠️  ISSUE: semantic_memory written but stats didn't increase")
        print(
            "   Possible cause: Stats query filters by packet_type LIKE 'memory_write_%'"
        )
        print("   But writes use packet_type 'memory.{kind}' (e.g., 'memory.note')")
        print("   FIX: Update stats query OR update write packet_type format")


if __name__ == "__main__":
    if not L9_EXECUTOR_API_KEY:
        print("ERROR: L9_EXECUTOR_API_KEY not set")
        print("Run: export L9_EXECUTOR_API_KEY=your_key")
    else:
        main()
