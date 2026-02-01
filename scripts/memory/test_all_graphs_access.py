#!/usr/bin/env python3
"""
Test All Graphs Access - Comprehensive Graph Readability Test
=============================================================

Tests access to all 8 graphs in L9 VPS memory via API.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Comprehensive Graph Readability Test",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "test_all_graphs_access",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j", "PostgreSQL"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

if not API_KEY:
    print("ERROR: L9_EXECUTOR_API_KEY not set")
    sys.exit(1)


async def test_all_graphs():
    """Test access to all 8 graphs."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    results = {}

    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        # =====================================================================
        # 1. PostgreSQL Packet Store
        # =====================================================================
        print("=" * 80)
        print("1. POSTGRESQL PACKET STORE")
        print("=" * 80)
        try:
            r = await client.get(f"{VPS_URL}/api/v1/memory/stats", headers=headers)
            if r.status_code == 200:
                data = r.json()
                results["packet_store"] = {
                    "status": "✅ ACCESSIBLE",
                    "packets": data.get("packets", 0),
                    "embeddings": data.get("embeddings", 0),
                    "facts": data.get("facts", 0),
                    "health": data.get("health", {}).get("status", "unknown"),
                }
                print(f"✅ Packets: {results['packet_store']['packets']:,}")
                print(f"✅ Embeddings: {results['packet_store']['embeddings']:,}")
                print(f"✅ Facts: {results['packet_store']['facts']:,}")
                print(f"✅ Health: {results['packet_store']['health']}")
            else:
                results["packet_store"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["packet_store"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 2. Semantic Memory (pgvector)
        # =====================================================================
        print("\n" + "=" * 80)
        print("2. SEMANTIC MEMORY (pgvector)")
        print("=" * 80)
        try:
            r = await client.post(
                f"{VPS_URL}/api/v1/memory/semantic/search",
                headers=headers,
                json={"query": "memory", "top_k": 5, "min_score": 0.0},
            )
            if r.status_code == 200:
                data = r.json()
                results_list = data.get("results", [])
                results["semantic_memory"] = {
                    "status": "✅ ACCESSIBLE",
                    "results_count": len(results_list),
                    "sample_scores": [r.get("score", 0) for r in results_list[:3]],
                }
                print(f"✅ Retrieved {len(results_list)} results")
                if results_list:
                    print(
                        f"✅ Sample scores: {results['semantic_memory']['sample_scores']}"
                    )
            else:
                results["semantic_memory"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["semantic_memory"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 3. Knowledge Facts
        # =====================================================================
        print("\n" + "=" * 80)
        print("3. KNOWLEDGE FACTS")
        print("=" * 80)
        try:
            r = await client.get(
                f"{VPS_URL}/api/v1/memory/facts", headers=headers, params={"limit": 10}
            )
            if r.status_code == 200:
                data = r.json()
                facts = data.get("facts", [])
                results["knowledge_facts"] = {
                    "status": "✅ ACCESSIBLE",
                    "count": data.get("count", 0),
                    "sample_count": len(facts),
                    "sample_facts": facts[:3] if facts else [],
                }
                print(f"✅ Total facts: {results['knowledge_facts']['count']}")
                print(f"✅ Sample retrieved: {len(facts)}")
                if facts:
                    f = facts[0]
                    print(f"✅ Example: {f.get('subject')} -> {f.get('predicate')}")
            else:
                results["knowledge_facts"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["knowledge_facts"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 4. Neo4j Knowledge Graph
        # =====================================================================
        print("\n" + "=" * 80)
        print("4. NEO4J KNOWLEDGE GRAPH")
        print("=" * 80)
        try:
            r = await client.post(
                f"{VPS_URL}/api/v1/memory/graph/query",
                headers=headers,
                json={
                    "query": "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC LIMIT 10",
                    "parameters": {},
                },
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    nodes = data.get("data", [])
                    results["neo4j_knowledge"] = {
                        "status": "✅ ACCESSIBLE",
                        "node_types": {n.get("label"): n.get("count") for n in nodes},
                        "total_node_types": len(nodes),
                    }
                    print(f"✅ Node types: {len(nodes)}")
                    for node in nodes[:5]:
                        print(f"   - {node.get('label')}: {node.get('count'):,}")
                else:
                    results["neo4j_knowledge"] = {
                        "status": f"❌ Query failed: {data.get('error')}"
                    }
            else:
                results["neo4j_knowledge"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["neo4j_knowledge"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 5. Agent State Graph
        # =====================================================================
        print("\n" + "=" * 80)
        print("5. AGENT STATE GRAPH")
        print("=" * 80)
        try:
            r = await client.post(
                f"{VPS_URL}/api/v1/memory/graph/query",
                headers=headers,
                json={
                    "query": """
                    MATCH (a:Agent)
                    OPTIONAL MATCH (a)-[:HAS_RESPONSIBILITY]->(r:Responsibility)
                    OPTIONAL MATCH (a)-[:HAS_DIRECTIVE]->(d:Directive)
                    OPTIONAL MATCH (a)-[:CAN_EXECUTE]->(t:Tool)
                    RETURN a.agent_id as agent_id,
                           a.designation as designation,
                           count(DISTINCT r) as responsibilities,
                           count(DISTINCT d) as directives,
                           count(DISTINCT t) as tools
                    LIMIT 10
                    """,
                    "parameters": {},
                },
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    agents = data.get("data", [])
                    results["agent_state"] = {
                        "status": "✅ ACCESSIBLE",
                        "agent_count": len(agents),
                        "agents": agents,
                    }
                    print(f"✅ Agents: {len(agents)}")
                    for agent in agents[:5]:
                        print(
                            f"   - {agent.get('agent_id')}: {agent.get('designation', 'N/A')}"
                        )
                else:
                    results["agent_state"] = {
                        "status": f"❌ Query failed: {data.get('error')}"
                    }
            else:
                results["agent_state"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["agent_state"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 6. Event Timeline
        # =====================================================================
        print("\n" + "=" * 80)
        print("6. EVENT TIMELINE")
        print("=" * 80)
        try:
            r = await client.post(
                f"{VPS_URL}/api/v1/memory/graph/query",
                headers=headers,
                json={
                    "query": """
                    MATCH (e:Event)
                    RETURN count(*) as total_events,
                           count(DISTINCT e.event_type) as event_types,
                           min(e.timestamp) as earliest,
                           max(e.timestamp) as latest
                    """,
                    "parameters": {},
                },
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success") and data.get("data"):
                    event_data = data["data"][0] if data["data"] else {}
                    results["event_timeline"] = {
                        "status": "✅ ACCESSIBLE",
                        "total_events": event_data.get("total_events", 0),
                        "event_types": event_data.get("event_types", 0),
                        "earliest": event_data.get("earliest"),
                        "latest": event_data.get("latest"),
                    }
                    print(
                        f"✅ Total events: {results['event_timeline']['total_events']}"
                    )
                    print(f"✅ Event types: {results['event_timeline']['event_types']}")
                else:
                    results["event_timeline"] = {
                        "status": f"❌ Query failed: {data.get('error')}"
                    }
            else:
                results["event_timeline"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["event_timeline"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 7. Repo Structure Graph
        # =====================================================================
        print("\n" + "=" * 80)
        print("7. REPO STRUCTURE GRAPH")
        print("=" * 80)
        try:
            r = await client.post(
                f"{VPS_URL}/api/v1/memory/graph/query",
                headers=headers,
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
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    repo_nodes = data.get("data", [])
                    results["repo_structure"] = {
                        "status": "✅ ACCESSIBLE",
                        "node_types": {
                            n.get("type"): n.get("count") for n in repo_nodes
                        },
                        "total_nodes": sum(n.get("count", 0) for n in repo_nodes),
                    }
                    print(
                        f"✅ Total repo nodes: {results['repo_structure']['total_nodes']}"
                    )
                    for node in repo_nodes[:5]:
                        print(f"   - {node.get('type')}: {node.get('count'):,}")
                else:
                    results["repo_structure"] = {
                        "status": f"❌ Query failed: {data.get('error')}"
                    }
            else:
                results["repo_structure"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["repo_structure"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # 8. World Model
        # =====================================================================
        print("\n" + "=" * 80)
        print("8. WORLD MODEL")
        print("=" * 80)
        try:
            # Try health check first
            r = await client.get(f"{VPS_URL}/world-model/health", headers=headers)
            if r.status_code == 200:
                data = r.json()
                results["world_model"] = {
                    "status": "✅ ACCESSIBLE",
                    "health": data.get("status", "unknown"),
                    "state_version": data.get("state_version", 0),
                    "entity_count": data.get("entity_count", 0),
                }
                print(f"✅ Health: {results['world_model']['health']}")
                print(f"✅ State version: {results['world_model']['state_version']}")
                print(f"✅ Entity count: {results['world_model']['entity_count']}")

                # Try listing entities
                r2 = await client.get(
                    f"{VPS_URL}/world-model/entities",
                    headers=headers,
                    params={"limit": 5},
                )
                if r2.status_code == 200:
                    entities_data = r2.json()
                    entities = entities_data.get("entities", [])
                    results["world_model"]["sample_entities"] = len(entities)
                    print(f"✅ Sample entities retrieved: {len(entities)}")
            elif r.status_code == 404:
                results["world_model"] = {
                    "status": "⚠️ NOT AVAILABLE (endpoint not found)"
                }
                print("⚠️ World Model API not available (endpoint not found)")
            else:
                results["world_model"] = {"status": f"❌ HTTP {r.status_code}"}
        except Exception as e:
            results["world_model"] = {"status": f"❌ ERROR: {e}"}
            print(f"❌ Error: {e}")

        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("\n" + "=" * 80)
        print("SUMMARY - GRAPH ACCESSIBILITY")
        print("=" * 80)

        accessible = sum(
            1 for r in results.values() if r.get("status", "").startswith("✅")
        )
        total = len(results)

        for name, result in results.items():
            status = result.get("status", "UNKNOWN")
            print(
                f"{'✅' if status.startswith('✅') else '❌' if status.startswith('❌') else '⚠️'} {name.upper().replace('_', ' ')}: {status}"
            )

        print("\n" + "=" * 80)
        print(f"ACCESSIBLE: {accessible}/{total} graphs")
        print("=" * 80)

        return results


if __name__ == "__main__":
    asyncio.run(test_all_graphs())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-034",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "auth",
        "event-driven",
        "http-client",
        "memory-substrate",
        "operations",
        "test",
        "testing",
    ],
    "keywords": ["all", "comprehensive", "graph", "graphs", "readability", "test"],
    "business_value": "Utility module for test all graphs access",
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
