#!/usr/bin/env python3
"""
L9 Graph Audit Script
=====================

Conducts a comprehensive audit of all graphs in L9 VPS memory:
1. PostgreSQL packet_store (packets, threads, lineage)
2. PostgreSQL semantic_memory (embeddings)
3. PostgreSQL knowledge_facts (facts)
4. Neo4j Knowledge Graph (entities, relationships, events)
5. Neo4j Agent State Graph (agent governance)
6. Neo4j Repo Structure Graph (codebase)
7. World Model (entities, updates, snapshots)

Usage:
    python3 scripts/audit_graphs.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Audit Graphs",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "audit_graphs",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

# Load environment
load_dotenv()

# =============================================================================
# PostgreSQL Queries
# =============================================================================


async def audit_postgresql_graphs() -> dict[str, Any]:
    """Audit PostgreSQL-based graphs."""
    try:
        from memory.substrate_repository import SubstrateRepository

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"error": "DATABASE_URL not set"}

        repo = SubstrateRepository(database_url=database_url)
        await repo.connect()

        results = {}

        # 1. Packet Store Audit
        print("\n📦 Auditing Packet Store...")
        packet_stats = await repo._execute_query("""
            SELECT
                COUNT(*) as total_packets,
                COUNT(DISTINCT thread_id) as total_threads,
                COUNT(DISTINCT packet_type) as packet_types,
                COUNT(*) FILTER (WHERE parent_ids IS NOT NULL AND array_length(parent_ids, 1) > 0) as packets_with_parents,
                COUNT(*) FILTER (WHERE ttl IS NOT NULL) as packets_with_ttl,
                COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as packets_with_tags,
                MIN(timestamp) as earliest_packet,
                MAX(timestamp) as latest_packet
            FROM packet_store
        """)

        packet_types = await repo._execute_query("""
            SELECT packet_type, COUNT(*) as count
            FROM packet_store
            GROUP BY packet_type
            ORDER BY count DESC
            LIMIT 20
        """)

        top_tags = await repo._execute_query("""
            SELECT unnest(tags) as tag, COUNT(*) as count
            FROM packet_store
            WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 20
        """)

        results["packet_store"] = {
            "stats": packet_stats[0] if packet_stats else {},
            "packet_types": packet_types,
            "top_tags": top_tags,
        }

        # 2. Semantic Memory Audit
        print("🔍 Auditing Semantic Memory (pgvector)...")
        semantic_stats = await repo._execute_query("""
            SELECT
                COUNT(*) as total_embeddings,
                COUNT(DISTINCT agent_id) as unique_agents,
                COUNT(DISTINCT packet_id) as unique_packets,
                MIN(created_at) as earliest_embedding,
                MAX(created_at) as latest_embedding
            FROM semantic_memory
        """)

        agent_breakdown = await repo._execute_query("""
            SELECT agent_id, COUNT(*) as count
            FROM semantic_memory
            GROUP BY agent_id
            ORDER BY count DESC
            LIMIT 20
        """)

        results["semantic_memory"] = {
            "stats": semantic_stats[0] if semantic_stats else {},
            "agent_breakdown": agent_breakdown,
        }

        # 3. Knowledge Facts Audit
        print("📚 Auditing Knowledge Facts...")
        facts_stats = await repo._execute_query("""
            SELECT
                COUNT(*) as total_facts,
                COUNT(DISTINCT subject) as unique_subjects,
                COUNT(DISTINCT predicate) as unique_predicates,
                AVG(confidence) as avg_confidence,
                MIN(confidence) as min_confidence,
                MAX(confidence) as max_confidence,
                COUNT(*) FILTER (WHERE source_packet IS NOT NULL) as facts_with_source,
                MIN(created_at) as earliest_fact,
                MAX(created_at) as latest_fact
            FROM knowledge_facts
        """)

        top_predicates = await repo._execute_query("""
            SELECT predicate, COUNT(*) as count
            FROM knowledge_facts
            GROUP BY predicate
            ORDER BY count DESC
            LIMIT 20
        """)

        top_subjects = await repo._execute_query("""
            SELECT subject, COUNT(*) as count
            FROM knowledge_facts
            GROUP BY subject
            ORDER BY count DESC
            LIMIT 20
        """)

        results["knowledge_facts"] = {
            "stats": facts_stats[0] if facts_stats else {},
            "top_predicates": top_predicates,
            "top_subjects": top_subjects,
        }

        # 4. Thread Lineage Audit
        print("🧵 Auditing Thread Lineage...")
        thread_stats = await repo._execute_query("""
            SELECT
                thread_id,
                COUNT(*) as packet_count,
                COUNT(*) FILTER (WHERE parent_ids IS NOT NULL AND array_length(parent_ids, 1) > 0) as packets_with_parents,
                MIN(timestamp) as thread_start,
                MAX(timestamp) as thread_end
            FROM packet_store
            WHERE thread_id IS NOT NULL
            GROUP BY thread_id
            ORDER BY packet_count DESC
            LIMIT 10
        """)

        results["threads"] = {
            "top_threads": thread_stats,
        }

        await repo.close()

        return results

    except Exception as e:
        logger.error(f"PostgreSQL audit failed: {e}")
        return {"error": str(e)}


# =============================================================================
# Neo4j Queries
# =============================================================================


async def audit_neo4j_graphs() -> dict[str, Any]:
    """Audit Neo4j-based graphs."""
    try:
        from memory.graph_client import get_neo4j_client

        neo4j = await get_neo4j_client()
        if not neo4j or not neo4j.is_available():
            return {"error": "Neo4j not available"}

        results = {}

        # 1. Overall Graph Stats
        print("\n🕸️  Auditing Neo4j Knowledge Graph...")
        overall_stats = await neo4j.run_query("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY count DESC
        """)

        results["overall_stats"] = overall_stats

        # 2. Relationship Stats
        relationship_stats = await neo4j.run_query("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(*) as count
            ORDER BY count DESC
        """)

        results["relationships"] = relationship_stats

        # 3. Entity Types Detail
        entity_details = {}
        for label in [
            "User",
            "Agent",
            "Event",
            "Entity",
            "Session",
            "Message",
            "HyperEvent",
        ]:
            stats = await neo4j.run_query(f"""
                MATCH (n:{label})
                RETURN count(*) as count,
                       collect(DISTINCT keys(n))[0] as sample_properties
                LIMIT 1
            """)
            if stats:
                entity_details[label] = stats[0]

        results["entity_details"] = entity_details

        # 4. Agent State Graph Audit
        print("🤖 Auditing Agent State Graph...")
        agent_state = await neo4j.run_query("""
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
        """)

        results["agent_state"] = agent_state

        # 5. Event Timeline Stats
        print("📅 Auditing Event Timeline...")
        event_stats = await neo4j.run_query("""
            MATCH (e:Event)
            RETURN count(*) as total_events,
                   count(DISTINCT e.event_type) as event_types,
                   min(e.timestamp) as earliest_event,
                   max(e.timestamp) as latest_event
        """)

        event_types = await neo4j.run_query("""
            MATCH (e:Event)
            RETURN e.event_type as type, count(*) as count
            ORDER BY count DESC
            LIMIT 20
        """)

        results["events"] = {
            "stats": event_stats[0] if event_stats else {},
            "event_types": event_types,
        }

        # 6. Repo Structure Graph Audit
        print("📁 Auditing Repo Structure Graph...")
        repo_stats = await neo4j.run_query("""
            MATCH (n)
            WHERE n:File OR n:Class OR n:Function OR n:Method OR n:Route
            RETURN labels(n)[0] as type, count(*) as count
            ORDER BY count DESC
        """)

        repo_relationships = await neo4j.run_query("""
            MATCH ()-[r]->()
            WHERE type(r) IN ['EXTENDS', 'HAS_METHOD', 'HANDLED_BY', 'IMPORTS', 'CONTAINS']
            RETURN type(r) as rel_type, count(*) as count
            ORDER BY count DESC
        """)

        results["repo_structure"] = {
            "nodes": repo_stats,
            "relationships": repo_relationships,
        }

        return results

    except Exception as e:
        logger.error(f"Neo4j audit failed: {e}")
        return {"error": str(e)}


# =============================================================================
# World Model Audit
# =============================================================================


async def audit_world_model() -> dict[str, Any]:
    """Audit World Model entities."""
    try:
        import asyncpg

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"error": "DATABASE_URL not set"}

        conn = await asyncpg.connect(database_url)

        results = {}

        # World Model Entities
        print("\n🌍 Auditing World Model...")
        entity_stats = await conn.fetch("""
            SELECT
                COUNT(*) as total_entities,
                COUNT(DISTINCT entity_type) as entity_types,
                AVG(confidence) as avg_confidence,
                MAX(version) as max_version,
                MIN(created_at) as earliest_entity,
                MAX(updated_at) as latest_update
            FROM world_model_entities
        """)

        entity_types = await conn.fetch("""
            SELECT entity_type, COUNT(*) as count
            FROM world_model_entities
            GROUP BY entity_type
            ORDER BY count DESC
        """)

        results["entities"] = {
            "stats": dict(entity_stats[0]) if entity_stats else {},
            "entity_types": [dict(r) for r in entity_types],
        }

        # World Model Updates
        update_stats = await conn.fetch("""
            SELECT
                COUNT(*) as total_updates,
                COUNT(DISTINCT insight_type) as insight_types,
                MAX(state_version_after) as current_state_version,
                MIN(applied_at) as earliest_update,
                MAX(applied_at) as latest_update
            FROM world_model_updates
        """)

        insight_types = await conn.fetch("""
            SELECT insight_type, COUNT(*) as count
            FROM world_model_updates
            GROUP BY insight_type
            ORDER BY count DESC
        """)

        results["updates"] = {
            "stats": dict(update_stats[0]) if update_stats else {},
            "insight_types": [dict(r) for r in insight_types],
        }

        # Snapshots
        snapshot_stats = await conn.fetch("""
            SELECT
                COUNT(*) as total_snapshots,
                MAX(state_version) as max_snapshot_version,
                MIN(created_at) as earliest_snapshot,
                MAX(created_at) as latest_snapshot
            FROM world_model_snapshots
        """)

        results["snapshots"] = {
            "stats": dict(snapshot_stats[0]) if snapshot_stats else {},
        }

        await conn.close()

        return results

    except Exception as e:
        logger.error(f"World Model audit failed: {e}")
        return {"error": str(e), "note": "World Model tables may not exist"}


# =============================================================================
# Main Audit Function
# =============================================================================


async def run_full_audit() -> dict[str, Any]:
    """Run comprehensive audit of all graphs."""
    print("=" * 80)
    print("L9 GRAPH AUDIT - Full System Scan")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    audit_results = {
        "timestamp": datetime.now().isoformat(),
        "postgresql": {},
        "neo4j": {},
        "world_model": {},
    }

    # PostgreSQL Graphs
    print("\n" + "=" * 80)
    print("POSTGRESQL GRAPHS")
    print("=" * 80)
    audit_results["postgresql"] = await audit_postgresql_graphs()

    # Neo4j Graphs
    print("\n" + "=" * 80)
    print("NEO4J GRAPHS")
    print("=" * 80)
    audit_results["neo4j"] = await audit_neo4j_graphs()

    # World Model
    print("\n" + "=" * 80)
    print("WORLD MODEL")
    print("=" * 80)
    audit_results["world_model"] = await audit_world_model()

    return audit_results


def print_audit_report(results: dict[str, Any]):
    """Print formatted audit report."""
    print("\n" + "=" * 80)
    print("AUDIT REPORT SUMMARY")
    print("=" * 80)

    # PostgreSQL Summary
    if "postgresql" in results and "error" not in results["postgresql"]:
        pg = results["postgresql"]
        print("\n📦 PACKET STORE:")
        if "packet_store" in pg:
            stats = pg["packet_store"]["stats"]
            print(f"   Total Packets:      {stats.get('total_packets', 0):,}")
            print(f"   Total Threads:      {stats.get('total_threads', 0):,}")
            print(f"   Packet Types:       {stats.get('packet_types', 0)}")
            print(f"   With Parents:       {stats.get('packets_with_parents', 0):,}")
            print(f"   With Tags:           {stats.get('packets_with_tags', 0):,}")
            print(f"   Earliest:           {stats.get('earliest_packet', 'N/A')}")
            print(f"   Latest:             {stats.get('latest_packet', 'N/A')}")

        print("\n🔍 SEMANTIC MEMORY (pgvector):")
        if "semantic_memory" in pg:
            stats = pg["semantic_memory"]["stats"]
            print(f"   Total Embeddings:   {stats.get('total_embeddings', 0):,}")
            print(f"   Unique Agents:      {stats.get('unique_agents', 0)}")
            print(f"   Unique Packets:     {stats.get('unique_packets', 0):,}")

        print("\n📚 KNOWLEDGE FACTS:")
        if "knowledge_facts" in pg:
            stats = pg["knowledge_facts"]["stats"]
            print(f"   Total Facts:         {stats.get('total_facts', 0):,}")
            print(f"   Unique Subjects:    {stats.get('unique_subjects', 0):,}")
            print(f"   Unique Predicates:  {stats.get('unique_predicates', 0)}")
            print(f"   Avg Confidence:     {stats.get('avg_confidence', 0):.2f}")

    # Neo4j Summary
    if "neo4j" in results and "error" not in results["neo4j"]:
        neo = results["neo4j"]
        print("\n🕸️  NEO4J KNOWLEDGE GRAPH:")
        if "overall_stats" in neo:
            print("   Node Types:")
            for item in neo["overall_stats"][:10]:
                print(f"      {item.get('label', 'Unknown')}: {item.get('count', 0):,}")

        if "relationships" in neo:
            print("\n   Relationship Types:")
            for item in neo["relationships"][:10]:
                print(
                    f"      {item.get('rel_type', 'Unknown')}: {item.get('count', 0):,}"
                )

        if "agent_state" in neo:
            print("\n🤖 AGENT STATE GRAPH:")
            for agent in neo["agent_state"]:
                print(f"   {agent.get('agent_id', 'Unknown')}:")
                print(f"      Responsibilities: {agent.get('responsibilities', 0)}")
                print(f"      Directives:       {agent.get('directives', 0)}")
                print(f"      SOPs:             {agent.get('sops', 0)}")
                print(f"      Tools:            {agent.get('tools', 0)}")
                print(f"      Supervisor:       {agent.get('supervisor', 'None')}")

        if "repo_structure" in neo and neo["repo_structure"]["nodes"]:
            print("\n📁 REPO STRUCTURE GRAPH:")
            for item in neo["repo_structure"]["nodes"]:
                print(f"   {item.get('type', 'Unknown')}: {item.get('count', 0):,}")

    # World Model Summary
    if "world_model" in results and "error" not in results["world_model"]:
        wm = results["world_model"]
        if "entities" in wm:
            print("\n🌍 WORLD MODEL:")
            stats = wm["entities"]["stats"]
            print(f"   Total Entities:     {stats.get('total_entities', 0):,}")
            print(f"   Entity Types:       {stats.get('entity_types', 0)}")
            print(f"   Current Version:   {stats.get('max_version', 0)}")

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)


async def main():
    """Main entry point."""
    try:
        results = await run_full_audit()
        print_audit_report(results)

        # Save to file
        output_file = (
            Path(__file__).parent.parent
            / "reports"
            / f"graph_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_file, "w") as f:
            await f.write(json.dumps(results, indent=2, default=str))
        print(f"\n📄 Full report saved to: {output_file}")

    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
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
    "dependencies": ["memory.graph_client", "memory.substrate_repository"],
    "tags": [
        "async",
        "event-driven",
        "filesystem",
        "logging",
        "memory-substrate",
        "messaging",
        "operations",
        "postgres",
        "serialization",
        "service",
    ],
    "keywords": [
        "audit",
        "full",
        "graphs",
        "model",
        "neo4j",
        "postgresql",
        "print",
        "report",
    ],
    "business_value": "Utility module for audit graphs",
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
