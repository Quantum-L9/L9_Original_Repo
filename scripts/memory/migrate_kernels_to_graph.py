#!/usr/bin/env python3
"""
Migrate Kernels to Graph
========================

One-time migration script to populate Neo4j graph with L's agent state
from YAML kernels. This enables the Graph-Backed Agent State feature.

Usage:
    # Run migration
    python scripts/migrate_kernels_to_graph.py

    # Verify migration
    python scripts/migrate_kernels_to_graph.py --verify

    # Force refresh (recreate all)
    python scripts/migrate_kernels_to_graph.py --force

Version: 1.0.0
Created: 2026-01-05
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Migrate Kernels To Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-09T01:57:28Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "migrate_kernels_to_graph",
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

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)


async def run_migration(force: bool = False) -> dict:
    """
    Run the kernel to graph migration.

    Args:
        force: If True, recreate all entities (normally uses MERGE)

    Returns:
        dict with migration statistics
    """
    from neo4j import AsyncGraphDatabase, basic_auth

    from core.agents.graph_state.bootstrap_l_graph import bootstrap_l_graph

    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv(
        "NEO4J_URI", "bolt://localhost:7687"
    )
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    logger.info(
        "Connecting to Neo4j",
        uri=neo4j_uri,
        user=neo4j_user,
    )

    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=basic_auth(neo4j_user, neo4j_password),
    )

    try:
        # Verify connection
        async with driver.session() as session:
            result = await session.run("RETURN 1 as n")
            await result.consume()

        logger.info("Neo4j connection verified")

        # Run bootstrap
        return await bootstrap_l_graph(
            neo4j_driver=driver,
            force_refresh=force,
        )

    finally:
        await driver.close()


async def verify_migration() -> dict:
    """
    Verify the migration was successful.

    Returns:
        dict with verification results
    """
    from neo4j import AsyncGraphDatabase, basic_auth

    from core.agents.graph_state.bootstrap_l_graph import verify_l_graph

    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv(
        "NEO4J_URI", "bolt://localhost:7687"
    )
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=basic_auth(neo4j_user, neo4j_password),
    )

    try:
        return await verify_l_graph(driver)

    finally:
        await driver.close()


async def main():
    """
    Performs the migration of YAML kernels to populate the Neo4j graph with agent state for graph-backed agent features.



    Raises:
        Exception: If migration fails due to connection or data errors
    """
    parser = argparse.ArgumentParser(description="Migrate YAML kernels to Neo4j graph")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration without running it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh all entities",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without doing it",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
        )

    if args.verify:
        logger.info("=" * 60)
        logger.info("VERIFYING L GRAPH STATE")
        logger.info("=" * 60)

        verification = await verify_migration()

        if verification.get("valid"):
            logger.info("\n✅ Verification PASSED\n")
            logger.info(f"  Agent ID: {verification['agent_id']}")
            logger.info(f"  Designation: {verification['designation']}")
            logger.info(f"  Responsibilities: {verification['responsibility_count']}")
            logger.info(f"  Directives: {verification['directive_count']}")
            logger.info(f"  SOPs: {verification['sop_count']}")
            logger.info(f"  Tools: {verification['tool_count']}")
            logger.info(f"  Supervisor: {verification['supervisor_id']}")
        else:
            logger.info("\n❌ Verification FAILED\n")
            logger.info(f"  Error: {verification.get('error', 'Unknown')}")
            sys.exit(1)

        return

    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN - Would migrate:")
        logger.info("=" * 60)

        from core.agents.graph_state.bootstrap_l_graph import (
            L_AGENT_CONFIG,
            L_DIRECTIVES,
            L_RESPONSIBILITIES,
            L_SOPS,
            L_TOOLS,
        )

        logger.info(
            f"\n  Agent: {L_AGENT_CONFIG['agent_id']} ({L_AGENT_CONFIG['designation']})"
        )
        logger.info(f"  Responsibilities: {len(L_RESPONSIBILITIES)}")
        for r in L_RESPONSIBILITIES:
            logger.info(f"    - {r['title']} (P{r['priority']})")

        logger.info(f"\n  Directives: {len(L_DIRECTIVES)}")
        for d in L_DIRECTIVES:
            logger.info(f"    - [{d['severity']}] {d['text'][:50]}...")

        logger.info(f"\n  SOPs: {len(L_SOPS)}")
        for s in L_SOPS:
            logger.info(f"    - {s['name']} ({len(s['steps'])} steps)")

        logger.info(f"\n  Tools: {len(L_TOOLS)}")
        for t in L_TOOLS:
            approval = "REQUIRES APPROVAL" if t["requires_approval"] else "no approval"
            logger.info(f"    - {t['name']} [{t['risk_level']}] ({approval})")

        logger.info("\n  Relationship: L REPORTS_TO igor")

        return

    # Run actual migration
    logger.info("=" * 60)
    logger.info("MIGRATING KERNELS TO GRAPH")
    logger.info("=" * 60)

    try:
        stats = await run_migration(force=args.force)

        logger.info("\n✅ Migration COMPLETE\n")
        logger.info(f"  Agent nodes: {stats['agent']}")
        logger.info(f"  Responsibilities: {stats['responsibilities']}")
        logger.info(f"  Directives: {stats['directives']}")
        logger.info(f"  SOPs: {stats['sops']}")
        logger.info(f"  Tools: {stats['tools']}")
        logger.info(f"  Relationships: {stats['relationships']}")

        logger.info("\n  Next steps:")
        logger.info("  1. Verify: python scripts/migrate_kernels_to_graph.py --verify")
        logger.info("  2. Enable: export L9_GRAPH_AGENT_STATE=true")
        logger.info("  3. Restart: docker compose up -d --build l9-api")

    except Exception as e:
        logger.info(f"\n❌ Migration FAILED: {e}")
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
    "dependencies": ["core.agents.graph_state.bootstrap_l_graph"],
    "tags": [
        "api",
        "async",
        "auth",
        "cli",
        "config",
        "debugging",
        "filesystem",
        "graph-db",
        "logging",
        "memory-substrate",
    ],
    "keywords": ["graph", "kernels", "migrate", "migration", "verify"],
    "business_value": "Utility module for migrate kernels to graph",
    "last_modified": "2026-01-09T01:57:28Z",
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
