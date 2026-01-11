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

import asyncio
import argparse
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
    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
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
        stats = await bootstrap_l_graph(
            neo4j_driver=driver,
            force_refresh=force,
        )
        
        return stats
        
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
    
    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=basic_auth(neo4j_user, neo4j_password),
    )
    
    try:
        verification = await verify_l_graph(driver)
        return verification
        
    finally:
        await driver.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate YAML kernels to Neo4j graph"
    )
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
            L_RESPONSIBILITIES,
            L_DIRECTIVES,
            L_SOPS,
            L_TOOLS,
        )
        
        logger.info(f"\n  Agent: {L_AGENT_CONFIG['agent_id']} ({L_AGENT_CONFIG['designation']})")
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
            approval = "REQUIRES APPROVAL" if t['requires_approval'] else "no approval"
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

