#!/usr/bin/env python3
"""
CLI script to bootstrap L's agent graph in Neo4j.

Usage:
    python scripts/run_bootstrap_l_graph.py

This populates Neo4j with L's:
- Agent node
- Responsibilities (4)
- Directives (5)
- SOPs (3)
- Tools (8)
- REPORTS_TO Igor relationship

Safe to run multiple times (idempotent via MERGE).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Run Bootstrap L Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T12:29:10Z",
    "updated_at": "2026-01-09T13:31:42Z",
    "layer": "operations",
    "domain": "agent_execution",
    "module_name": "run_bootstrap_l_graph",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import AsyncGraphDatabase


async def main():
    # Get Neo4j credentials from environment
    # Check both NEO4J_URI and NEO4J_URL (docker-compose uses URL)
    neo4j_uri = os.getenv("NEO4J_URI") or os.getenv(
        "NEO4J_URL", "bolt://localhost:7687"
    )
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    print(f"Connecting to Neo4j at {neo4j_uri}...")

    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
    )

    try:
        # Verify connection
        async with driver.session() as session:
            result = await session.run("RETURN 1 as test")
            await result.single()
        print("✅ Connected to Neo4j")

        # Run bootstrap
        from core.agents.graph_state.bootstrap_l_graph import (
            bootstrap_l_graph, verify_l_graph)

        print("\n🚀 Running bootstrap_l_graph()...")
        stats = await bootstrap_l_graph(driver)

        print("\n📊 Bootstrap Results:")
        print(f"   Agent:           {stats['agent']}")
        print(f"   Responsibilities: {stats['responsibilities']}")
        print(f"   Directives:       {stats['directives']}")
        print(f"   SOPs:            {stats['sops']}")
        print(f"   Tools:           {stats['tools']}")
        print(f"   Relationships:   {stats['relationships']}")

        # Verify
        print("\n🔍 Verifying L's graph...")
        verification = await verify_l_graph(driver)

        if verification["valid"]:
            print("✅ L's graph is VALID")
            print(f"   Agent ID:        {verification['agent_id']}")
            print(f"   Designation:     {verification['designation']}")
            print(f"   Responsibilities: {verification['responsibility_count']}")
            print(f"   Directives:      {verification['directive_count']}")
            print(f"   SOPs:            {verification['sop_count']}")
            print(f"   Tools:           {verification['tool_count']}")
            print(f"   Supervisor:      {verification['supervisor_id']}")
        else:
            print(f"❌ L's graph is INVALID: {verification.get('error')}")
            sys.exit(1)

    finally:
        await driver.close()

    print("\n✅ Bootstrap complete!")


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
    "dependencies": ["core.agents.graph_state.bootstrap_l_graph"],
    "tags": [
        "agent-execution",
        "async",
        "auth",
        "graph-db",
        "operations",
        "service",
        "testing",
    ],
    "keywords": ["bootstrap", "graph"],
    "business_value": "Agent node Responsibilities (4) Directives (5) SOPs (3) Tools (8) REPORTS_TO Igor relationship Safe to run multiple times (idempotent via MERGE).",
    "last_modified": "2026-01-09T13:31:42Z",
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
