#!/usr/bin/env python3
"""
index_tool_usage.py - Index Tool Usage Patterns to Neo4j Graph
===============================================================

Queries tool_audit_log table, extracts tool usage patterns (usage_count, success_rate),
and creates Neo4j nodes (Tool {name, usage_count, success_rate}) linked to agents via USES relationship.

Created: 2026-01-09
Version: 1.0.0

Usage:
    python3 scripts/index_tool_usage.py [--dry-run] [--verbose]

Features:
- Queries tool_audit_log table for tool usage statistics
- Calculates usage_count and success_rate per tool
- Creates Neo4j Tool nodes with metrics
- Links tools to agents via USES relationship
- Uses Neo4j HTTP API (VPS)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Index Tool Usage Patterns to Neo4j Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "index_tool_usage",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import structlog
import httpx
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv()

logger = structlog.get_logger(__name__)

# Configuration
VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


async def query_tool_usage_stats(database_url: str) -> List[Dict[str, Any]]:
    """
    Query tool_audit_log table for tool usage statistics.

    Returns:
        List of dicts with tool_name, agent_id, usage_count, success_count, total_duration_ms, avg_cost_usd
    """
    try:
        import asyncpg

        conn = await asyncpg.connect(database_url)
        try:
            # Aggregate tool usage by tool_name and agent_id
            rows = await conn.fetch("""
                SELECT 
                    tool_name,
                    agent_id,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN error IS NULL THEN 1 ELSE 0 END) as success_count,
                    AVG(duration_ms) as avg_duration_ms,
                    SUM(duration_ms) as total_duration_ms,
                    AVG(cost_usd) as avg_cost_usd,
                    SUM(cost_usd) as total_cost_usd,
                    MIN(timestamp) as first_used,
                    MAX(timestamp) as last_used
                FROM tool_audit_log
                GROUP BY tool_name, agent_id
                ORDER BY usage_count DESC
            """)

            stats = []
            for row in rows:
                usage_count = row["usage_count"]
                success_count = row["success_count"]
                success_rate = success_count / usage_count if usage_count > 0 else 0.0

                stats.append(
                    {
                        "tool_name": row["tool_name"],
                        "agent_id": row["agent_id"],
                        "usage_count": usage_count,
                        "success_count": success_count,
                        "success_rate": success_rate,
                        "avg_duration_ms": float(row["avg_duration_ms"] or 0),
                        "total_duration_ms": float(row["total_duration_ms"] or 0),
                        "avg_cost_usd": float(row["avg_cost_usd"] or 0),
                        "total_cost_usd": float(row["total_cost_usd"] or 0),
                        "first_used": row["first_used"].isoformat()
                        if row["first_used"]
                        else None,
                        "last_used": row["last_used"].isoformat()
                        if row["last_used"]
                        else None,
                    }
                )

            return stats
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to query tool usage stats: {e}", exc_info=True)
        return []


async def api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make authenticated API request to VPS."""
    if not API_KEY:
        return {"error": "L9_EXECUTOR_API_KEY not set", "success": False}

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{VPS_URL}{endpoint}"

    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
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
            logger.error(f"API request failed: {e}")
            return {"error": str(e), "success": False}


async def execute_cypher(
    query: str, parameters: Optional[Dict] = None
) -> Dict[str, Any]:
    """Execute Cypher query via VPS API."""
    return await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={"query": query, "parameters": parameters or {}},
    )


async def index_tool_usage_to_neo4j(
    tool_stats: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Index tool usage patterns to Neo4j graph.

    Creates:
    - Tool nodes with usage metrics
    - Agent nodes (if not exist)
    - USES relationships between agents and tools
    """
    if dry_run:
        logger.info(f"DRY RUN - would index {len(tool_stats)} tool usage patterns")
        return {"tools_indexed": len(tool_stats), "dry_run": True}

    tools_indexed = 0
    relationships_created = 0
    errors = []

    # Batch process tools (50 at a time)
    batch_size = 50
    for i in range(0, len(tool_stats), batch_size):
        batch = tool_stats[i : i + batch_size]

        # Create Tool nodes and USES relationships
        query = """
        UNWIND $tools AS tool
        MERGE (t:Tool {name: tool.tool_name})
        SET t.usage_count = tool.usage_count,
            t.success_rate = tool.success_rate,
            t.avg_duration_ms = tool.avg_duration_ms,
            t.total_duration_ms = tool.total_duration_ms,
            t.avg_cost_usd = tool.avg_cost_usd,
            t.total_cost_usd = tool.total_cost_usd,
            t.first_used = tool.first_used,
            t.last_used = tool.last_used,
            t.updated_at = datetime()
        WITH t, tool
        MERGE (a:Agent {id: tool.agent_id})
        SET a.updated_at = datetime()
        WITH t, a, tool
        MERGE (a)-[r:USES]->(t)
        SET r.usage_count = tool.usage_count,
            r.success_rate = tool.success_rate,
            r.last_used = tool.last_used,
            r.updated_at = datetime()
        RETURN count(t) as tools_created, count(r) as relationships_created
        """

        try:
            result = await execute_cypher(query, {"tools": batch})
            if result.get("success"):
                tools_indexed += len(batch)
                relationships_created += len(batch)
            else:
                errors.append(
                    f"Batch {i // batch_size + 1}: {result.get('error', 'Unknown error')}"
                )
        except Exception as e:
            logger.error(f"Failed to index batch {i // batch_size + 1}: {e}")
            errors.append(f"Batch {i // batch_size + 1}: {str(e)}")

    return {
        "tools_indexed": tools_indexed,
        "relationships_created": relationships_created,
        "errors": errors,
        "status": "success" if not errors else "partial",
    }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main indexing function."""
    logger.info("Starting tool usage indexing", dry_run=dry_run)

    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return

    # Query tool usage statistics
    logger.info("Querying tool_audit_log table...")
    tool_stats = await query_tool_usage_stats(DATABASE_URL)
    logger.info(f"Found {len(tool_stats)} tool usage patterns")

    if not tool_stats:
        logger.warning("No tool usage data found")
        return

    if verbose:
        logger.info("Sample tool stats:")
        for stat in tool_stats[:5]:
            logger.info(
                f"  {stat['tool_name']} by {stat['agent_id']}: "
                f"{stat['usage_count']} uses, {stat['success_rate']:.2%} success"
            )

    # Index to Neo4j
    result = await index_tool_usage_to_neo4j(tool_stats, dry_run=dry_run)

    # Summary
    logger.info("=" * 60)
    logger.info("TOOL USAGE INDEXING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Tool patterns found: {len(tool_stats)}")
    logger.info(f"  Tools indexed: {result.get('tools_indexed', 0)}")
    logger.info(f"  Relationships created: {result.get('relationships_created', 0)}")
    if result.get("errors"):
        logger.warning(f"  Errors: {len(result['errors'])}")
        for error in result["errors"][:5]:
            logger.warning(f"    - {error}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Index tool usage patterns to Neo4j graph"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

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
        "batch-processing",
        "cli",
        "filesystem",
        "http-client",
        "logging",
        "memory-substrate",
        "metrics",
    ],
    "keywords": [
        "api",
        "cypher",
        "execute",
        "graph",
        "index",
        "neo4j",
        "patterns",
        "query",
    ],
    "business_value": "Utility module for index tool usage",
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
