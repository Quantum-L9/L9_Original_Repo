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
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import structlog

# Add project root to path

logger = structlog.get_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# VPS Configuration
VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

if not API_KEY:
    logger.error("error: l9_executor_api_key not set in environment")
    sys.exit(1)


async def api_request(method: str, endpoint: str, **kwargs) -> dict[str, Any]:
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


async def audit_memory_stats() -> dict[str, Any]:
    """Get memory system stats."""
    logger.info("📊 fetching memory stats...")
    return await api_request("GET", "/api/v1/memory/stats")


async def audit_packets(limit: int = 10) -> dict[str, Any]:
    """Audit packet store via semantic search."""
    logger.info("📦 auditing packets...")

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


async def audit_facts(limit: int = 20) -> dict[str, Any]:
    """Audit knowledge facts."""
    logger.info("📚 auditing knowledge facts...")

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


async def audit_neo4j_via_api() -> dict[str, Any]:
    """Query Neo4j via graph API endpoint."""
    logger.info("🕸️  querying neo4j via api...")

    results = {}

    # 1. Overall node stats
    logger.info("   getting node counts...")
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
    logger.info("   getting relationship counts...")
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
    logger.info("   getting agent state...")
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
    logger.info("   getting event stats...")
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
    logger.info("   getting repo structure...")
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


async def run_audit() -> dict[str, Any]:
    """Run full audit."""
    logger.info("=" * 80)
    logger.info("l9 graph audit - vps api")
    logger.info("=" * 80)
    logger.info("vps url: vps url", VPS_URL=VPS_URL)
    logger.info("timestamp: {datetime.now(tz=UTC).isoformat()}")
    results = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
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


def print_report(results: dict[str, Any]):
    """Print formatted report."""
    logger.info("\n" + "=" * 80)
    logger.info("audit report")
    logger.info("=" * 80)

    # Memory Stats
    stats = results.get("memory_stats", {})
    if "error" not in stats:
        logger.info("\n📊 memory stats:")
        logger.info("   status:            {stats.get('status', 'unknown')}")
        logger.info("   total packets:     {stats.get('packets', 0):,}")
        logger.info("   total embeddings:  {stats.get('embeddings', 0):,}")
        logger.info("   total facts:       {stats.get('facts', 0):,}")

        health = stats.get("health", {})
        if health:
            logger.info("\n   health status:     {health.get('status', 'unknown')}")
            components = health.get("components", {})
            if components:
                logger.info("   components:")
                for comp_name, comp_data in components.items():
                    logger.info(
                        "      comp name: {comp data.get('status', 'unknown')}",
                        comp_name=comp_name,
                    )

    # Packets
    packets = results.get("packets", {})
    if "error" not in packets:
        logger.info("\n📦 packets:")
        logger.info("   sample retrieved:  {packets.get('total_found', 0)}")
        sample = packets.get("sample_packets", [])
        if sample:
            logger.info("   sample count:      {len(sample)}")
            # Show packet types
            types = {}
            for p in sample:
                ptype = p.get("packet_type", "unknown")
                types[ptype] = types.get(ptype, 0) + 1
            logger.info("   sample types:")
            for ptype, count in types.items():
                logger.info("      ptype: count", ptype=ptype, count=count)

    # Facts
    facts = results.get("facts", {})
    if "error" not in facts:
        logger.info("\n📚 knowledge facts:")
        logger.info("   total facts:       {facts.get('total_facts', 0):,}")

        top_preds = facts.get("top_predicates", [])
        if top_preds:
            logger.info("   top predicates:")
            for pred, count in top_preds[:5]:
                logger.info("      pred: count", pred=pred, count=count)

        top_subjs = facts.get("top_subjects", [])
        if top_subjs:
            logger.info("   top subjects:")
            for subj, count in top_subjs[:5]:
                logger.info("      subj: count", subj=subj, count=count)

    # Neo4j
    neo4j = results.get("neo4j", {})
    if "error" not in neo4j:
        logger.info("\n🕸️  neo4j knowledge graph:")

        node_stats = neo4j.get("node_stats", [])
        if node_stats:
            logger.info("   node types:")
            for item in node_stats[:15]:
                label = item.get("label") or "Unknown"
                count = item.get("count", 0)
                logger.info("      label: {count:,}", label=label)

        rel_stats = neo4j.get("relationship_stats", [])
        if rel_stats:
            logger.info("\n   relationship types:")
            for item in rel_stats[:15]:
                rel_type = item.get("rel_type") or "Unknown"
                count = item.get("count", 0)
                logger.info("      rel type: {count:,}", rel_type=rel_type)

        agent_state = neo4j.get("agent_state", [])
        if agent_state:
            logger.info("\n🤖 agent state graph:")
            for agent in agent_state:
                agent_id = agent.get("agent_id", "Unknown")
                logger.info("   agent id:", agent_id=agent_id)
                logger.info("      designation:     {agent.get('designation', 'n/a')}")
                logger.info(
                    "      responsibilities: {agent.get('responsibilities', 0)}"
                )
                logger.info("      directives:       {agent.get('directives', 0)}")
                logger.info("      sops:             {agent.get('sops', 0)}")
                logger.info("      tools:            {agent.get('tools', 0)}")
                logger.info("      supervisor:       {agent.get('supervisor', 'none')}")

        events = neo4j.get("events", {})
        if events:
            stats = events.get("stats", {})
            if stats:
                logger.info("\n📅 event timeline:")
                logger.info("   total events:      {stats.get('total_events', 0):,}")
                logger.info("   event types:       {stats.get('event_types', 0)}")
                logger.info(
                    "   earliest:          {stats.get('earliest_event', 'n/a')}"
                )
                logger.info("   latest:             {stats.get('latest_event', 'n/a')}")

        repo = neo4j.get("repo_structure", [])
        if repo:
            logger.info("\n📁 repo structure graph:")
            for item in repo[:10]:
                node_type = item.get("type") or "Unknown"
                count = item.get("count", 0)
                logger.info("   node type: {count:,}", node_type=node_type)
    elif "error" in neo4j:
        logger.info("\n🕸️  neo4j:")
        logger.error("   error: {neo4j.get('error', 'unknown error')}")

    logger.info("\n" + "=" * 80)


async def main():
    """Main entry point."""
    try:
        results = await run_audit()
        print_report(results)

        # Save to file
        output_file = (
            Path(__file__).parent.parent
            / "reports"
            / f"graph_audit_vps_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_file, "w") as f:
            await f.write(json.dumps(results, indent=2, default=str))
        logger.info("\n📄 full report saved to: output file", output_file=output_file)

    except Exception as e:
        logger.error("error: e", e=e)
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
