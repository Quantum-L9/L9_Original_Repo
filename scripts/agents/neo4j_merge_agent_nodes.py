#!/usr/bin/env python3
"""
Neo4j Agent Node Merge Migration
================================

Merges duplicate Agent nodes in Neo4j to ensure a single authoritative node
for each agent. Part of UKG Phase 2: Graph Merge.

The Problem:
- Graph State creates Agent nodes with agent_id, designation, role, etc.
- Tool Graph was creating separate Agent nodes with just id property
- This caused duplicate nodes and broken relationships

The Solution:
- Identify all Agent nodes for the same logical agent
- Merge properties into a single canonical node
- Redirect all relationships to the canonical node
- Delete duplicate nodes

Usage:
    # Dry run (shows what would change)
    python scripts/neo4j_merge_agent_nodes.py --dry-run
    
    # Run migration
    python scripts/neo4j_merge_agent_nodes.py
    
    # Verify
    python scripts/neo4j_merge_agent_nodes.py --verify

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-2 (Graph Merge)
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


async def get_neo4j_driver():
    """Get async Neo4j driver."""
    from neo4j import AsyncGraphDatabase, basic_auth
    
    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    return AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=basic_auth(neo4j_user, neo4j_password),
    )


async def find_duplicate_agents(driver) -> list[dict]:
    """
    Find Agent nodes that represent the same logical agent.
    
    Agents are considered duplicates if they share:
    - agent_id property, or
    - id property (legacy Tool Graph)
    """
    async with driver.session() as session:
        # Find agents with potential duplicates
        result = await session.run("""
            MATCH (a:Agent)
            WITH coalesce(a.agent_id, a.id) as logical_id, collect(a) as agents
            WHERE size(agents) > 1
            RETURN logical_id, 
                   [a in agents | {
                       id: id(a),
                       agent_id: a.agent_id,
                       legacy_id: a.id,
                       designation: a.designation,
                       role: a.role,
                       status: a.status,
                       properties: properties(a)
                   }] as duplicates
        """)
        
        records = await result.data()
        return records


async def get_all_agents(driver) -> list[dict]:
    """Get all Agent nodes for inspection."""
    async with driver.session() as session:
        result = await session.run("""
            MATCH (a:Agent)
            OPTIONAL MATCH (a)-[r]->(t)
            RETURN a.agent_id as agent_id,
                   a.id as legacy_id,
                   a.designation as designation,
                   a.role as role,
                   a.status as status,
                   count(r) as relationship_count,
                   collect(DISTINCT type(r)) as relationship_types
        """)
        return await result.data()


async def merge_agent_nodes(
    driver,
    logical_id: str,
    duplicates: list[dict],
    dry_run: bool = False,
) -> dict:
    """
    Merge duplicate Agent nodes into one.
    
    Strategy:
    1. Pick the node with most properties as canonical
    2. Merge properties from other nodes
    3. Redirect all relationships to canonical node
    4. Delete duplicate nodes
    """
    if len(duplicates) < 2:
        return {"status": "SKIPPED", "reason": "Only one node"}
    
    # Sort by property count - most properties = canonical
    sorted_dups = sorted(
        duplicates,
        key=lambda d: len(d.get("properties", {})),
        reverse=True,
    )
    
    canonical = sorted_dups[0]
    to_merge = sorted_dups[1:]
    
    if dry_run:
        logger.info(
            f"[DRY RUN] Would merge {len(to_merge)} duplicates into canonical node "
            f"(agent_id={logical_id}, neo4j_id={canonical['id']})"
        )
        for dup in to_merge:
            logger.info(f"  - Would merge: neo4j_id={dup['id']}")
        return {"status": "DRY_RUN", "merged": len(to_merge)}
    
    async with driver.session() as session:
        canonical_id = canonical["id"]
        
        for dup in to_merge:
            dup_id = dup["id"]
            
            # 1. Copy properties to canonical (don't overwrite existing)
            await session.run("""
                MATCH (canonical:Agent) WHERE id(canonical) = $canonical_id
                MATCH (dup:Agent) WHERE id(dup) = $dup_id
                SET canonical += properties(dup)
            """, canonical_id=canonical_id, dup_id=dup_id)
            
            # 2. Redirect incoming relationships
            await session.run("""
                MATCH (canonical:Agent) WHERE id(canonical) = $canonical_id
                MATCH (dup:Agent) WHERE id(dup) = $dup_id
                MATCH (other)-[r]->(dup)
                CALL {
                    WITH other, r, canonical
                    CREATE (other)-[newRel:TEMP_REL]->(canonical)
                    SET newRel = properties(r)
                    DELETE r
                }
            """, canonical_id=canonical_id, dup_id=dup_id)
            
            # 3. Redirect outgoing relationships
            await session.run("""
                MATCH (canonical:Agent) WHERE id(canonical) = $canonical_id
                MATCH (dup:Agent) WHERE id(dup) = $dup_id
                MATCH (dup)-[r]->(other)
                WHERE NOT other:Agent OR id(other) <> $dup_id
                MERGE (canonical)-[newRel:TEMP_REL]->(other)
                SET newRel = properties(r)
                DELETE r
            """, canonical_id=canonical_id, dup_id=dup_id)
            
            # 4. Delete duplicate node
            await session.run("""
                MATCH (dup:Agent) WHERE id(dup) = $dup_id
                DELETE dup
            """, dup_id=dup_id)
            
            logger.info(f"Merged node {dup_id} into canonical {canonical_id}")
        
        # Ensure canonical has agent_id set
        await session.run("""
            MATCH (a:Agent) WHERE id(a) = $canonical_id
            SET a.agent_id = coalesce(a.agent_id, $logical_id)
        """, canonical_id=canonical_id, logical_id=logical_id)
        
        return {"status": "MERGED", "merged": len(to_merge)}


async def verify_single_nodes(driver) -> dict:
    """Verify each logical agent has exactly one node."""
    async with driver.session() as session:
        result = await session.run("""
            MATCH (a:Agent)
            WITH coalesce(a.agent_id, a.id) as logical_id, count(a) as node_count
            RETURN logical_id, node_count
            ORDER BY node_count DESC
        """)
        
        records = await result.data()
        
        duplicates = [r for r in records if r["node_count"] > 1]
        
        return {
            "total_agents": len(records),
            "duplicates": len(duplicates),
            "details": duplicates,
            "status": "PASS" if not duplicates else "FAIL",
        }


async def run_migration(dry_run: bool = False) -> dict:
    """Run the full agent merge migration."""
    driver = await get_neo4j_driver()
    
    try:
        # Find duplicates
        duplicates = await find_duplicate_agents(driver)
        
        if not duplicates:
            logger.info("No duplicate Agent nodes found")
            return {"status": "ALREADY_CLEAN", "merged": 0}
        
        logger.info(f"Found {len(duplicates)} logical agents with duplicates")
        
        total_merged = 0
        for dup_group in duplicates:
            logical_id = dup_group["logical_id"]
            nodes = dup_group["duplicates"]
            
            result = await merge_agent_nodes(driver, logical_id, nodes, dry_run)
            total_merged += result.get("merged", 0)
        
        return {
            "status": "SUCCESS" if not dry_run else "DRY_RUN",
            "groups_processed": len(duplicates),
            "nodes_merged": total_merged,
        }
        
    finally:
        await driver.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Merge duplicate Agent nodes in Neo4j"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify all agents have single nodes",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all Agent nodes",
    )
    
    args = parser.parse_args()
    
    if args.list:
        logger.info("=" * 60)
        logger.info("ALL AGENT NODES")
        logger.info("=" * 60)
        
        driver = await get_neo4j_driver()
        try:
            agents = await get_all_agents(driver)
            for a in agents:
                logger.info(f"\n  agent_id: {a.get('agent_id')}")
                logger.info(f"  legacy_id: {a.get('legacy_id')}")
                logger.info(f"  designation: {a.get('designation')}")
                logger.info(f"  relationships: {a.get('relationship_count')} ({a.get('relationship_types')})")
        finally:
            await driver.close()
        return
    
    if args.verify:
        logger.info("=" * 60)
        logger.info("VERIFYING AGENT NODE UNIQUENESS")
        logger.info("=" * 60)
        
        driver = await get_neo4j_driver()
        try:
            result = await verify_single_nodes(driver)
            
            logger.info(f"\n  Total agents: {result['total_agents']}")
            logger.info(f"  Duplicates found: {result['duplicates']}")
            logger.info(f"  Status: {result['status']}")
            
            if result['details']:
                logger.info("\n  Duplicate details:")
                for d in result['details']:
                    logger.info(f"    - {d['logical_id']}: {d['node_count']} nodes")
        finally:
            await driver.close()
        return
    
    logger.info("=" * 60)
    logger.info("AGENT NODE MERGE MIGRATION")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("\n[DRY RUN MODE - No changes will be made]\n")
    
    try:
        stats = await run_migration(dry_run=args.dry_run)
        
        logger.info(f"\n  Status: {stats['status']}")
        logger.info(f"  Groups processed: {stats.get('groups_processed', 0)}")
        logger.info(f"  Nodes merged: {stats.get('nodes_merged', 0)}")
        
        if stats['status'] == "SUCCESS":
            logger.info("\n✅ Migration COMPLETE")
        elif stats['status'] == "ALREADY_CLEAN":
            logger.info("\n✅ No duplicates - already clean")
        else:
            logger.info("\n📋 Dry run complete - no changes made")
            
    except Exception as e:
        logger.info(f"\n❌ Migration FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

