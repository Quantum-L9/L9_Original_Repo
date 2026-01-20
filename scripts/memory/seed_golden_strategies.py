#!/usr/bin/env python3
"""
Seed Golden Strategies for Strategy Memory
==========================================

Seeds the Strategy Memory with manually curated high-value strategies
for common L9 task patterns.

Phase 0: Manual seeding of golden strategies
Phase 1: Automatic capture will add more

Usage:
    python scripts/memory/seed_golden_strategies.py
    python scripts/memory/seed_golden_strategies.py --list
    python scripts/memory/seed_golden_strategies.py --delete-all

GMP-102: Strategy Memory Phase 0-1
Version: 1.0.0
Created: 2026-01-20
"""

import argparse
import asyncio
import sys
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Golden Strategy Definitions
# =============================================================================

GOLDEN_STRATEGIES: List[Dict[str, Any]] = [
    {
        "name": "Research and Report",
        "description": "Research a topic using multiple sources, analyze findings, and produce a structured report",
        "task_kind": "research",
        "tags": ["research", "report", "analysis", "summary"],
        "plan_payload": {
            "strategy_type": "research_report",
            "steps": [
                {
                    "order": 1,
                    "action": "search",
                    "description": "Search for relevant information using web search tools",
                    "agent": "researcher",
                    "parameters": {"max_sources": 5, "timeout_seconds": 30},
                },
                {
                    "order": 2,
                    "action": "analyze",
                    "description": "Analyze and synthesize findings from search results",
                    "agent": "analyst",
                    "parameters": {"depth": "comprehensive"},
                },
                {
                    "order": 3,
                    "action": "summarize",
                    "description": "Create structured summary with key findings",
                    "agent": "writer",
                    "parameters": {
                        "format": "markdown",
                        "sections": ["summary", "findings", "recommendations"],
                    },
                },
            ],
            "expected_outputs": ["report_markdown", "key_findings_list"],
            "typical_duration_ms": 30000,
        },
    },
    {
        "name": "Code Analysis and Review",
        "description": "Analyze code structure, identify patterns, evaluate quality, and provide recommendations",
        "task_kind": "code_analysis",
        "tags": ["code", "analysis", "review", "quality"],
        "plan_payload": {
            "strategy_type": "code_review",
            "steps": [
                {
                    "order": 1,
                    "action": "parse",
                    "description": "Parse code structure and extract key components",
                    "agent": "analyzer",
                    "parameters": {"depth": "full", "include_tests": True},
                },
                {
                    "order": 2,
                    "action": "evaluate",
                    "description": "Evaluate code quality against L9 patterns",
                    "agent": "evaluator",
                    "parameters": {"patterns": ["L9_PATTERNS", "ANTI_PATTERNS"]},
                },
                {
                    "order": 3,
                    "action": "recommend",
                    "description": "Generate improvement recommendations",
                    "agent": "advisor",
                    "parameters": {"priority": "impact", "max_recommendations": 10},
                },
            ],
            "expected_outputs": ["quality_score", "recommendations_list"],
            "typical_duration_ms": 20000,
        },
    },
    {
        "name": "Multi-Step Planning",
        "description": "Break down complex goal into actionable steps with dependencies",
        "task_kind": "planning",
        "tags": ["planning", "decomposition", "tasks", "workflow"],
        "plan_payload": {
            "strategy_type": "task_decomposition",
            "steps": [
                {
                    "order": 1,
                    "action": "analyze_goal",
                    "description": "Analyze the high-level goal and constraints",
                    "agent": "planner",
                    "parameters": {
                        "extract": ["requirements", "constraints", "success_criteria"]
                    },
                },
                {
                    "order": 2,
                    "action": "decompose",
                    "description": "Break goal into sub-tasks with clear boundaries",
                    "agent": "planner",
                    "parameters": {"max_depth": 3, "parallelizable": True},
                },
                {
                    "order": 3,
                    "action": "sequence",
                    "description": "Determine execution order and dependencies",
                    "agent": "orchestrator",
                    "parameters": {"optimize_for": "speed"},
                },
                {
                    "order": 4,
                    "action": "validate",
                    "description": "Validate plan completeness and feasibility",
                    "agent": "validator",
                    "parameters": {"check": ["coverage", "dependencies", "resources"]},
                },
            ],
            "expected_outputs": ["execution_plan", "dependency_graph"],
            "typical_duration_ms": 15000,
        },
    },
    {
        "name": "Documentation Generation",
        "description": "Generate comprehensive documentation from code and context",
        "task_kind": "documentation",
        "tags": ["docs", "documentation", "readme", "generation"],
        "plan_payload": {
            "strategy_type": "doc_generation",
            "steps": [
                {
                    "order": 1,
                    "action": "extract_info",
                    "description": "Extract docstrings, types, and structure from code",
                    "agent": "extractor",
                    "parameters": {"include": ["functions", "classes", "modules"]},
                },
                {
                    "order": 2,
                    "action": "enrich",
                    "description": "Enrich with examples and usage patterns",
                    "agent": "writer",
                    "parameters": {"add_examples": True, "style": "technical"},
                },
                {
                    "order": 3,
                    "action": "format",
                    "description": "Format documentation in target format",
                    "agent": "formatter",
                    "parameters": {"format": "markdown", "template": "l9_readme"},
                },
            ],
            "expected_outputs": ["readme_markdown", "api_docs"],
            "typical_duration_ms": 25000,
        },
    },
    {
        "name": "Error Diagnosis and Fix",
        "description": "Diagnose error, identify root cause, and propose fix",
        "task_kind": "debugging",
        "tags": ["debug", "error", "fix", "diagnosis"],
        "plan_payload": {
            "strategy_type": "error_resolution",
            "steps": [
                {
                    "order": 1,
                    "action": "parse_error",
                    "description": "Parse error message and stack trace",
                    "agent": "parser",
                    "parameters": {"extract": ["error_type", "location", "context"]},
                },
                {
                    "order": 2,
                    "action": "diagnose",
                    "description": "Identify root cause by analyzing code path",
                    "agent": "debugger",
                    "parameters": {"depth": "thorough", "check_related": True},
                },
                {
                    "order": 3,
                    "action": "propose_fix",
                    "description": "Generate fix proposal with explanation",
                    "agent": "fixer",
                    "parameters": {"include_tests": True, "verify": True},
                },
            ],
            "expected_outputs": ["root_cause", "fix_proposal", "test_case"],
            "typical_duration_ms": 20000,
        },
    },
]


# =============================================================================
# Seeding Functions
# =============================================================================


async def seed_golden_strategies(
    neo4j_client: Any,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Seed golden strategies into Neo4j.

    Args:
        neo4j_client: Neo4j client instance
        force: If True, overwrite existing strategies

    Returns:
        Summary of seeding operation
    """
    from memory.neo4j_strategy_memory import Neo4jStrategyMemoryService

    service = Neo4jStrategyMemoryService(neo4j_client=neo4j_client)

    results = {
        "total": len(GOLDEN_STRATEGIES),
        "created": 0,
        "skipped": 0,
        "errors": 0,
        "strategy_ids": [],
    }

    for strategy_def in GOLDEN_STRATEGIES:
        try:
            # Generate a placeholder embedding (1536-dim zeros)
            # In production, would use SemanticService to generate real embeddings
            context_embedding = [0.0] * 1536

            # Check if strategy with same name exists (simple dedup)
            existing = await _check_existing_strategy(
                neo4j_client, strategy_def["name"]
            )

            if existing and not force:
                logger.info(
                    "strategy_exists_skipping",
                    name=strategy_def["name"],
                )
                results["skipped"] += 1
                continue

            if existing and force:
                # Delete existing before recreating
                await _delete_strategy_by_name(neo4j_client, strategy_def["name"])
                logger.info(
                    "deleted_existing_strategy",
                    name=strategy_def["name"],
                )

            # Record the strategy
            strategy_id = await service.record_new_strategy(
                task_id=f"golden_{strategy_def['task_kind']}",
                description=strategy_def["description"],
                plan_payload=strategy_def["plan_payload"],
                context_embedding=context_embedding,
                tags=strategy_def["tags"],
            )

            results["created"] += 1
            results["strategy_ids"].append(strategy_id)

            logger.info(
                "golden_strategy_seeded",
                strategy_id=strategy_id,
                name=strategy_def["name"],
                task_kind=strategy_def["task_kind"],
            )

        except Exception as e:
            results["errors"] += 1
            logger.error(
                "golden_strategy_seed_failed",
                name=strategy_def["name"],
                error=str(e),
            )

    return results


async def list_strategies(neo4j_client: Any) -> List[Dict[str, Any]]:
    """List all strategies in Neo4j."""
    query = """
    MATCH (s:Strategy)
    RETURN s.id as id, s.name as name, s.task_kind as task_kind,
           s.performance_score as score, s.usage_count as usage,
           s.tags as tags, s.created_at as created
    ORDER BY s.created_at DESC
    """

    result = await neo4j_client.execute_query(query, {})
    return result or []


async def delete_all_strategies(neo4j_client: Any) -> int:
    """Delete all strategies and executions."""
    query = """
    MATCH (s:Strategy)
    OPTIONAL MATCH (s)-[:EXECUTED_AS]->(e:Execution)
    DETACH DELETE s, e
    RETURN count(s) as deleted
    """

    result = await neo4j_client.execute_query(query, {})
    return result[0]["deleted"] if result else 0


async def _check_existing_strategy(neo4j_client: Any, name: str) -> bool:
    """Check if a strategy with given name exists."""
    query = "MATCH (s:Strategy {name: $name}) RETURN count(s) > 0 as exists"
    result = await neo4j_client.execute_query(query, {"name": name})
    return result[0]["exists"] if result else False


async def _delete_strategy_by_name(neo4j_client: Any, name: str) -> None:
    """Delete a strategy by name."""
    query = """
    MATCH (s:Strategy {name: $name})
    OPTIONAL MATCH (s)-[:EXECUTED_AS]->(e:Execution)
    DETACH DELETE s, e
    """
    await neo4j_client.execute_query(query, {"name": name})


# =============================================================================
# CLI Interface
# =============================================================================


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed golden strategies for Strategy Memory"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing strategies",
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all strategies (dangerous!)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing strategies",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be seeded without actually seeding",
    )

    args = parser.parse_args()

    # Initialize Neo4j client
    try:
        from memory.graph_client import get_neo4j_client

        neo4j = await get_neo4j_client()
        if not neo4j or not await neo4j.is_available():
            logger.error("Neo4j not available")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

    try:
        if args.list:
            # List existing strategies
            strategies = await list_strategies(neo4j)
            print("\n=== Existing Strategies ===\n")
            if not strategies:
                print("No strategies found.")
            else:
                for s in strategies:
                    print(f"  {s['id']}: {s['name']}")
                    print(
                        f"    Kind: {s['task_kind']}, Score: {s['score']:.2f}, Usage: {s['usage']}"
                    )
                    print(f"    Tags: {', '.join(s['tags'] or [])}")
                    print()
            return

        if args.delete_all:
            # Confirm deletion
            confirm = input("Are you sure you want to delete ALL strategies? [y/N] ")
            if confirm.lower() != "y":
                print("Cancelled.")
                return

            deleted = await delete_all_strategies(neo4j)
            print(f"Deleted {deleted} strategies.")
            return

        if args.dry_run:
            # Show what would be seeded
            print("\n=== Dry Run: Golden Strategies to Seed ===\n")
            for strategy in GOLDEN_STRATEGIES:
                print(f"  - {strategy['name']}")
                print(f"    Kind: {strategy['task_kind']}")
                print(f"    Tags: {', '.join(strategy['tags'])}")
                print(f"    Description: {strategy['description'][:60]}...")
                print()
            print(f"Total: {len(GOLDEN_STRATEGIES)} strategies")
            return

        # Seed golden strategies
        print("\n=== Seeding Golden Strategies ===\n")
        results = await seed_golden_strategies(neo4j, force=args.force)

        print("\nResults:")
        print(f"  Created: {results['created']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Total: {results['total']}")

        if results["strategy_ids"]:
            print("\nNew Strategy IDs:")
            for sid in results["strategy_ids"]:
                print(f"  - {sid}")

    finally:
        # Close Neo4j connection
        try:
            from memory.graph_client import close_neo4j_client

            await close_neo4j_client()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
