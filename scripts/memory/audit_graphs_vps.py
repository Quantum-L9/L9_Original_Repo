#!/usr/bin/env python3
"""
L9 Graph Audit Script - VPS API Version
========================================

Queries VPS memory API to audit all graphs.
Uses HTTP API instead of direct database connections.

Usage:
    python3 scripts/audit_graphs_vps.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "VPS API Version",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "audit_graphs_vps",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import json

import aiofiles
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# VPS Configuration
VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

if not API_KEY:
    print("ERROR: L9_EXECUTOR_API_KEY not set in environment")
    sys.exit(1)


async def api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make authenticated API request to VPS."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{VPS_URL}{endpoint}"

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None),
            }


async def audit_memory_stats() -> Dict[str, Any]:
    """Get memory system stats."""
    print("📊 Fetching memory stats...")
    result = await api_request("GET", "/api/v1/memory/stats")
    return result


async def audit_packets(limit: int = 10) -> Dict[str, Any]:
    """Audit packet store via semantic search."""
    print("📦 Auditing packets...")

    # Get sample packets via search
    result = await api_request(
        "POST",
        "/api/v1/memory/semantic/search",
        json={
            "query": "memory",
            "top_k": limit,
            "min_score": 0.0,
        },
    )

    return {
        "sample_packets": result.get("results", [])[:limit],
        "total_found": len(result.get("results", [])),
    }


async def audit_facts(limit: int = 20) -> Dict[str, Any]:
    """Audit knowledge facts."""
    print("📚 Auditing knowledge facts...")

    result = await api_request("GET", "/api/v1/memory/facts", params={"limit": limit})

    facts = result.get("facts", [])

    # Analyze facts
    predicates = {}
    subjects = {}
    for fact in facts:
        pred = fact.get("predicate", "unknown")
        subj = fact.get("subject", "unknown")
        predicates[pred] = predicates.get(pred, 0) + 1
        subjects[subj] = subjects.get(subj, 0) + 1

    return {
        "total_facts": result.get("count", 0),
        "sample_facts": facts[:10],
        "top_predicates": sorted(predicates.items(), key=lambda x: x[1], reverse=True)[
            :10
        ],
        "top_subjects": sorted(subjects.items(), key=lambda x: x[1], reverse=True)[:10],
    }


async def audit_neo4j_via_api() -> Dict[str, Any]:
    """Query Neo4j via graph API endpoint."""
    print("🕸️  Querying Neo4j via API...")

    results = {}

    # 1. Overall node stats
    print("   Getting node counts...")
    node_stats = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC",
            "parameters": {},
        },
    )

    if node_stats.get("success") and "data" in node_stats:
        results["node_stats"] = node_stats.get("data", [])
    else:
        results["node_stats_error"] = node_stats.get("error", "Query failed")

    # 2. Relationship stats
    print("   Getting relationship counts...")
    rel_stats = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": "MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count ORDER BY count DESC",
            "parameters": {},
        },
    )

    if rel_stats.get("success") and "data" in rel_stats:
        results["relationship_stats"] = rel_stats.get("data", [])
    else:
        results["relationship_stats_error"] = rel_stats.get("error", "Query failed")

    # 3. Agent state graph
    print("   Getting agent state...")
    agent_state = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": """
        MATCH (a:Agent)
        OPTIONAL MATCH (a)-[:HAS_RESPONSIBILITY]->(r:Responsibility)
        OPTIONAL MATCH (a)-[:HAS_DIRECTIVE]->(d:Directive)
        OPTIONAL MATCH (a)-[:HAS_SOP]->(s:SOP)
        OPTIONAL MATCH (a)-[:CAN_EXECUTE]->(t:Tool)
        OPTIONAL MATCH (a)-[:REPORTS_TO]->(supervisor:Agent)
        RETURN a.agent_id as agent_id,
               a.designation as designation,
               count(DISTINCT r) as responsibilities,
               count(DISTINCT d) as directives,
               count(DISTINCT s) as sops,
               count(DISTINCT t) as tools,
               supervisor.agent_id as supervisor
        """,
            "parameters": {},
        },
    )

    if agent_state.get("success") and "data" in agent_state:
        results["agent_state"] = agent_state.get("data", [])
    else:
        results["agent_state_error"] = agent_state.get("error", "Query failed")

    # 4. Event timeline stats
    print("   Getting event stats...")
    event_stats = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": """
        MATCH (e:Event)
        RETURN count(*) as total_events,
               count(DISTINCT e.event_type) as event_types,
               min(e.timestamp) as earliest_event,
               max(e.timestamp) as latest_event
        """,
            "parameters": {},
        },
    )

    event_types = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": """
        MATCH (e:Event)
        RETURN e.event_type as type, count(*) as count
        ORDER BY count DESC
        LIMIT 20
        """,
            "parameters": {},
        },
    )

    if event_stats.get("success") and "data" in event_stats:
        results["events"] = {
            "stats": (
                event_stats.get("data", [{}])[0] if event_stats.get("data") else {}
            ),
            "event_types": (
                event_types.get("data", [])
                if event_types.get("success") and "data" in event_types
                else []
            ),
        }
    else:
        results["events_error"] = event_stats.get("error", "Query failed")

    # 5. Repo structure graph
    print("   Getting repo structure...")
    repo_stats = await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={
            "query": """
        MATCH (n)
        WHERE n:File OR n:Class OR n:Function OR n:Method OR n:Route
        RETURN labels(n)[0] as type, count(*) as count
        ORDER BY count DESC
        """,
            "parameters": {},
        },
    )

    if repo_stats.get("success") and "data" in repo_stats:
        results["repo_structure"] = repo_stats.get("data", [])
    else:
        results["repo_structure_error"] = repo_stats.get("error", "Query failed")

    return results


async def run_audit() -> Dict[str, Any]:
    """Run full audit."""
    print("=" * 80)
    print("L9 GRAPH AUDIT - VPS API")
    print("=" * 80)
    print(f"VPS URL: {VPS_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "vps_url": VPS_URL,
        "memory_stats": {},
        "packets": {},
        "facts": {},
        "neo4j": {},
    }

    # Memory Stats
    stats = await audit_memory_stats()
    results["memory_stats"] = stats

    # Packets
    packets = await audit_packets()
    results["packets"] = packets

    # Facts
    facts = await audit_facts()
    results["facts"] = facts

    # Neo4j (placeholder)
    neo4j = await audit_neo4j_via_api()
    results["neo4j"] = neo4j

    return results


def print_report(results: Dict[str, Any]):
    """Print formatted report."""
    print("\n" + "=" * 80)
    print("AUDIT REPORT")
    print("=" * 80)

    # Memory Stats
    stats = results.get("memory_stats", {})
    if "error" not in stats:
        print("\n📊 MEMORY STATS:")
        print(f"   Status:            {stats.get('status', 'unknown')}")
        print(f"   Total Packets:     {stats.get('packets', 0):,}")
        print(f"   Total Embeddings:  {stats.get('embeddings', 0):,}")
        print(f"   Total Facts:       {stats.get('facts', 0):,}")

        health = stats.get("health", {})
        if health:
            print(f"\n   Health Status:     {health.get('status', 'unknown')}")
            components = health.get("components", {})
            if components:
                print("   Components:")
                for comp_name, comp_data in components.items():
                    print(f"      {comp_name}: {comp_data.get('status', 'unknown')}")

    # Packets
    packets = results.get("packets", {})
    if "error" not in packets:
        print("\n📦 PACKETS:")
        print(f"   Sample Retrieved:  {packets.get('total_found', 0)}")
        sample = packets.get("sample_packets", [])
        if sample:
            print(f"   Sample Count:      {len(sample)}")
            # Show packet types
            types = {}
            for p in sample:
                ptype = p.get("packet_type", "unknown")
                types[ptype] = types.get(ptype, 0) + 1
            print("   Sample Types:")
            for ptype, count in types.items():
                print(f"      {ptype}: {count}")

    # Facts
    facts = results.get("facts", {})
    if "error" not in facts:
        print("\n📚 KNOWLEDGE FACTS:")
        print(f"   Total Facts:       {facts.get('total_facts', 0):,}")

        top_preds = facts.get("top_predicates", [])
        if top_preds:
            print("   Top Predicates:")
            for pred, count in top_preds[:5]:
                print(f"      {pred}: {count}")

        top_subjs = facts.get("top_subjects", [])
        if top_subjs:
            print("   Top Subjects:")
            for subj, count in top_subjs[:5]:
                print(f"      {subj}: {count}")

    # Neo4j
    neo4j = results.get("neo4j", {})
    if "error" not in neo4j:
        print("\n🕸️  NEO4J KNOWLEDGE GRAPH:")

        node_stats = neo4j.get("node_stats", [])
        if node_stats:
            print("   Node Types:")
            for item in node_stats[:15]:
                label = item.get("label") or "Unknown"
                count = item.get("count", 0)
                print(f"      {label}: {count:,}")

        rel_stats = neo4j.get("relationship_stats", [])
        if rel_stats:
            print("\n   Relationship Types:")
            for item in rel_stats[:15]:
                rel_type = item.get("rel_type") or "Unknown"
                count = item.get("count", 0)
                print(f"      {rel_type}: {count:,}")

        agent_state = neo4j.get("agent_state", [])
        if agent_state:
            print("\n🤖 AGENT STATE GRAPH:")
            for agent in agent_state:
                agent_id = agent.get("agent_id", "Unknown")
                print(f"   {agent_id}:")
                print(f"      Designation:     {agent.get('designation', 'N/A')}")
                print(f"      Responsibilities: {agent.get('responsibilities', 0)}")
                print(f"      Directives:       {agent.get('directives', 0)}")
                print(f"      SOPs:             {agent.get('sops', 0)}")
                print(f"      Tools:            {agent.get('tools', 0)}")
                print(f"      Supervisor:       {agent.get('supervisor', 'None')}")

        events = neo4j.get("events", {})
        if events:
            stats = events.get("stats", {})
            if stats:
                print("\n📅 EVENT TIMELINE:")
                print(f"   Total Events:      {stats.get('total_events', 0):,}")
                print(f"   Event Types:       {stats.get('event_types', 0)}")
                print(f"   Earliest:          {stats.get('earliest_event', 'N/A')}")
                print(f"   Latest:             {stats.get('latest_event', 'N/A')}")

        repo = neo4j.get("repo_structure", [])
        if repo:
            print("\n📁 REPO STRUCTURE GRAPH:")
            for item in repo[:10]:
                node_type = item.get("type") or "Unknown"
                count = item.get("count", 0)
                print(f"   {node_type}: {count:,}")
    elif "error" in neo4j:
        print("\n🕸️  NEO4J:")
        print(f"   Error: {neo4j.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)


async def main():
    """Main entry point."""
    try:
        results = await run_audit()
        print_report(results)

        # Save to file
        output_file = (
            Path(__file__).parent.parent
            / "reports"
            / f"graph_audit_vps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_file, "w") as f:
            await f.write(json.dumps(results, indent=2, default=str))
        print(f"\n📄 Full report saved to: {output_file}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

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
        "event-driven",
        "filesystem",
        "http-client",
        "memory-substrate",
        "operations",
        "serialization",
        "service",
    ],
    "keywords": [
        "api",
        "audit",
        "facts",
        "memory",
        "neo4j",
        "packets",
        "print",
        "report",
    ],
    "business_value": "Utility module for audit graphs vps",
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
