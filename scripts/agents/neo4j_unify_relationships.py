#!/usr/bin/env python3
"""
Neo4j Relationship Unification Migration
=========================================

Migrates legacy HAS_TOOL relationships to unified CAN_EXECUTE relationship.
Part of UKG Phase 1: Schema Unification.

This migration:
1. Finds all (Agent)-[:HAS_TOOL]->(Tool) relationships
2. Creates equivalent (Agent)-[:CAN_EXECUTE]->(Tool) relationships
3. Optionally deletes the legacy HAS_TOOL relationships

The migration is idempotent - running it multiple times is safe.

Usage:
    # Dry run (shows what would change)
    python scripts/neo4j_unify_relationships.py --dry-run
    
    # Run migration
    python scripts/neo4j_unify_relationships.py
    
    # Run and delete legacy relationships
    python scripts/neo4j_unify_relationships.py --delete-legacy
    
    # Verify migration
    python scripts/neo4j_unify_relationships.py --verify

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-1 (Schema Unification)
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

# Relationship type constants
LEGACY_REL = "HAS_TOOL"
UNIFIED_REL = "CAN_EXECUTE"


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


async def count_relationships(driver, rel_type: str) -> int:
    """Count relationships of a given type."""
    async with driver.session() as session:
        result = await session.run(
            f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        )
        record = await result.single()
        return record["count"] if record else 0


async def get_legacy_relationships(driver) -> list[dict]:
    """Get all legacy HAS_TOOL relationships with their properties."""
    async with driver.session() as session:
        result = await session.run(f"""
            MATCH (a:Agent)-[r:{LEGACY_REL}]->(t:Tool)
            RETURN a.agent_id as agent_id, 
                   a.id as agent_id_alt,
                   t.name as tool_name,
                   t.id as tool_id_alt,
                   properties(r) as props
        """)
        records = await result.data()
        return records


async def migrate_relationship(
    driver,
    agent_id: str,
    tool_id: str,
    properties: dict,
    dry_run: bool = False,
) -> bool:
    """
    Migrate a single HAS_TOOL relationship to CAN_EXECUTE.
    
    Args:
        driver: Neo4j driver
        agent_id: Agent identifier
        tool_id: Tool identifier
        properties: Relationship properties to preserve
        dry_run: If True, only log what would happen
    
    Returns:
        True if successful
    """
    if dry_run:
        logger.info(
            f"[DRY RUN] Would migrate: ({agent_id})-[:{LEGACY_REL}]->({tool_id}) "
            f"to ({agent_id})-[:{UNIFIED_REL}]->({tool_id})"
        )
        return True
    
    async with driver.session() as session:
        # Create new CAN_EXECUTE relationship (if not exists)
        await session.run(f"""
            MATCH (a:Agent), (t:Tool)
            WHERE (a.agent_id = $agent_id OR a.id = $agent_id)
              AND (t.name = $tool_id OR t.id = $tool_id)
            MERGE (a)-[r:{UNIFIED_REL}]->(t)
            SET r += $props
        """, agent_id=agent_id, tool_id=tool_id, props=properties or {})
        
        logger.info(
            f"Migrated: ({agent_id})-[:{UNIFIED_REL}]->({tool_id})"
        )
        return True


async def delete_legacy_relationships(driver, dry_run: bool = False) -> int:
    """
    Delete all legacy HAS_TOOL relationships.
    
    Args:
        driver: Neo4j driver
        dry_run: If True, only log what would happen
    
    Returns:
        Number of relationships deleted
    """
    count = await count_relationships(driver, LEGACY_REL)
    
    if dry_run:
        logger.info(f"[DRY RUN] Would delete {count} legacy {LEGACY_REL} relationships")
        return count
    
    async with driver.session() as session:
        result = await session.run(f"""
            MATCH ()-[r:{LEGACY_REL}]->()
            DELETE r
            RETURN count(r) as deleted
        """)
        record = await result.single()
        deleted = record["deleted"] if record else 0
        
        logger.info(f"Deleted {deleted} legacy {LEGACY_REL} relationships")
        return deleted


async def verify_migration(driver) -> dict:
    """
    Verify migration was successful.
    
    Returns:
        dict with verification results
    """
    legacy_count = await count_relationships(driver, LEGACY_REL)
    unified_count = await count_relationships(driver, UNIFIED_REL)
    
    return {
        "legacy_count": legacy_count,
        "unified_count": unified_count,
        "migration_complete": legacy_count == 0 and unified_count > 0,
        "status": "COMPLETE" if legacy_count == 0 else "PENDING",
    }


async def run_migration(dry_run: bool = False, delete_legacy: bool = False) -> dict:
    """
    Run the full migration.
    
    Args:
        dry_run: If True, only show what would change
        delete_legacy: If True, delete legacy relationships after migration
    
    Returns:
        dict with migration statistics
    """
    driver = await get_neo4j_driver()
    
    try:
        # Get current counts
        legacy_count = await count_relationships(driver, LEGACY_REL)
        unified_count = await count_relationships(driver, UNIFIED_REL)
        
        logger.info(
            f"Before migration: {LEGACY_REL}={legacy_count}, {UNIFIED_REL}={unified_count}"
        )
        
        if legacy_count == 0:
            logger.info("No legacy relationships to migrate")
            return {
                "status": "ALREADY_COMPLETE",
                "legacy_before": 0,
                "unified_before": unified_count,
                "migrated": 0,
            }
        
        # Get legacy relationships
        legacy_rels = await get_legacy_relationships(driver)
        logger.info(f"Found {len(legacy_rels)} legacy relationships to migrate")
        
        # Migrate each relationship
        migrated = 0
        for rel in legacy_rels:
            agent_id = rel.get("agent_id") or rel.get("agent_id_alt")
            tool_id = rel.get("tool_name") or rel.get("tool_id_alt")
            props = rel.get("props", {})
            
            if agent_id and tool_id:
                if await migrate_relationship(driver, agent_id, tool_id, props, dry_run):
                    migrated += 1
        
        # Delete legacy if requested
        deleted = 0
        if delete_legacy and not dry_run:
            deleted = await delete_legacy_relationships(driver)
        elif delete_legacy and dry_run:
            deleted = await delete_legacy_relationships(driver, dry_run=True)
        
        # Verify
        final_legacy = await count_relationships(driver, LEGACY_REL)
        final_unified = await count_relationships(driver, UNIFIED_REL)
        
        return {
            "status": "SUCCESS" if not dry_run else "DRY_RUN",
            "legacy_before": legacy_count,
            "unified_before": unified_count,
            "migrated": migrated,
            "deleted": deleted,
            "legacy_after": final_legacy,
            "unified_after": final_unified,
        }
        
    finally:
        await driver.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate HAS_TOOL relationships to CAN_EXECUTE"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    parser.add_argument(
        "--delete-legacy",
        action="store_true",
        help="Delete legacy HAS_TOOL relationships after migration",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration status",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verify:
        logger.info("=" * 60)
        logger.info("VERIFYING RELATIONSHIP MIGRATION")
        logger.info("=" * 60)
        
        driver = await get_neo4j_driver()
        try:
            verification = await verify_migration(driver)
            
            logger.info(f"\n  Legacy ({LEGACY_REL}): {verification['legacy_count']}")
            logger.info(f"  Unified ({UNIFIED_REL}): {verification['unified_count']}")
            logger.info(f"  Status: {verification['status']}")
            
            if verification['migration_complete']:
                logger.info("\n✅ Migration COMPLETE")
            else:
                logger.info("\n⚠️ Migration PENDING")
                logger.info(f"   Run: python scripts/neo4j_unify_relationships.py --delete-legacy")
        finally:
            await driver.close()
        return
    
    logger.info("=" * 60)
    logger.info("RELATIONSHIP UNIFICATION MIGRATION")
    logger.info(f"  {LEGACY_REL} → {UNIFIED_REL}")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("\n[DRY RUN MODE - No changes will be made]\n")
    
    try:
        stats = await run_migration(
            dry_run=args.dry_run,
            delete_legacy=args.delete_legacy,
        )
        
        logger.info(f"\n  Status: {stats['status']}")
        logger.info(f"  Legacy before: {stats['legacy_before']}")
        logger.info(f"  Unified before: {stats['unified_before']}")
        logger.info(f"  Migrated: {stats['migrated']}")
        
        if 'deleted' in stats:
            logger.info(f"  Deleted: {stats['deleted']}")
        
        if 'legacy_after' in stats:
            logger.info(f"  Legacy after: {stats['legacy_after']}")
            logger.info(f"  Unified after: {stats['unified_after']}")
        
        if stats['status'] == "SUCCESS":
            logger.info("\n✅ Migration COMPLETE")
        elif stats['status'] == "ALREADY_COMPLETE":
            logger.info("\n✅ Already migrated - no changes needed")
        else:
            logger.info("\n📋 Dry run complete - no changes made")
            logger.info("   Run without --dry-run to apply changes")
        
    except Exception as e:
        logger.info(f"\n❌ Migration FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

