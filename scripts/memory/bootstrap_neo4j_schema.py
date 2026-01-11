#!/usr/bin/env python3
"""
Bootstrap Neo4j Schema for L9 Agent Governance

Creates required labels, indexes, and initial governance entities for the L agent.
Eliminates Neo4j "label not found" warnings by ensuring all expected schema exists.
Establishes the complete governance graph including kernel bindings and authority hierarchy.

Labels Created:
- Responsibility: Agent governance responsibilities
- Directive: Agent operational directives  
- SOP: Standard Operating Procedures
- Kernel: Governance kernels (10 kernels: master, identity, cognitive, etc.)

Relationships Created:
- HAS_RESPONSIBILITY: Agent → Responsibility
- HAS_DIRECTIVE: Agent → Directive
- HAS_SOP: Agent → SOP
- GOVERNED_BY: Agent → Kernel (L governed by 10 kernels)
- GUARDED_BY: Tool → Kernel (high-risk tools guarded by Safety Kernel)
- REPORTS_TO: Agent → Agent (L reports to igor)

Usage:
    python scripts/bootstrap_neo4j_schema.py
    
Or from API startup:
    from scripts.bootstrap_neo4j_schema import bootstrap_l_governance
    await bootstrap_l_governance(neo4j_driver)

Author: L9 System
Created: 2026-01-06
Updated: 2026-01-06 (GMP-34: Added Kernel, GOVERNED_BY, GUARDED_BY, REPORTS_TO)
"""

import asyncio
import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = structlog.get_logger(__name__)

# L Agent's Core Governance Entities
L_RESPONSIBILITIES = [
    {
        "id": "resp-strategic-tech-decisions",
        "name": "Strategic Technical Decisions",
        "description": "Make high-level technical decisions for L9 architecture and implementation",
        "priority": "HIGH",
    },
    {
        "id": "resp-code-quality",
        "name": "Code Quality Assurance",
        "description": "Ensure all code meets L9 quality standards and passes governance checks",
        "priority": "HIGH",
    },
    {
        "id": "resp-memory-management",
        "name": "Memory Substrate Management",
        "description": "Maintain and optimize the memory substrate for efficient retrieval",
        "priority": "MEDIUM",
    },
]

L_DIRECTIVES = [
    {
        "id": "dir-no-destructive-ops",
        "name": "No Destructive Operations Without Approval",
        "description": "All destructive operations (git push, file delete, etc.) require Igor approval",
        "enforced": True,
    },
    {
        "id": "dir-audit-trail",
        "name": "Maintain Audit Trail",
        "description": "All decisions and tool calls must be logged to memory substrate",
        "enforced": True,
    },
    {
        "id": "dir-surgical-edits",
        "name": "Surgical Edits Only",
        "description": "Use search_replace for file edits, never rewrite entire files",
        "enforced": True,
    },
]

L_SOPS = [
    {
        "id": "sop-gmp-execution",
        "name": "GMP Execution Protocol",
        "description": "Follow GMP phases 0-6 for all tracked code changes",
        "doc_ref": ".cursor-commands/commands/gmp.md",
    },
    {
        "id": "sop-state-sync",
        "name": "State Sync Before Edits",
        "description": "Read workflow_state.md before any code modifications",
        "doc_ref": "workflow_state.md",
    },
    {
        "id": "sop-ynp-decision",
        "name": "YNP Decision Framework",
        "description": "Use Yes/No/Proceed framework for decision making with confidence scoring",
        "doc_ref": ".cursor-commands/commands/ynp.md",
    },
    {
        "id": "sop-reasoning-mode",
        "name": "Multi-Modal Reasoning",
        "description": "Apply abductive, deductive, inductive reasoning for complex problems",
        "doc_ref": ".cursor-commands/commands/reasoning.md",
    },
    {
        "id": "sop-analyze-evaluate",
        "name": "Analyze + Evaluate Protocol",
        "description": "Deep codebase analysis before making changes",
        "doc_ref": ".cursor-commands/commands/analyze_evaluate.md",
    },
]

# L9 Governance Kernels (10 kernels loaded at startup)
L_KERNELS = [
    {
        "id": "kernel-01-master",
        "name": "Master Kernel",
        "file": "01_master_kernel.yaml",
        "purpose": "Core governance coordination and kernel stack orchestration",
        "priority": 1,
    },
    {
        "id": "kernel-02-identity",
        "name": "Identity Kernel",
        "file": "02_identity_kernel.yaml",
        "purpose": "L agent identity, persona, and role definition",
        "priority": 2,
    },
    {
        "id": "kernel-03-cognitive",
        "name": "Cognitive Kernel",
        "file": "03_cognitive_kernel.yaml",
        "purpose": "Reasoning patterns, decision frameworks, problem-solving strategies",
        "priority": 3,
    },
    {
        "id": "kernel-04-behavioral",
        "name": "Behavioral Kernel",
        "file": "04_behavioral_kernel.yaml",
        "purpose": "Communication style, interaction patterns, response formatting",
        "priority": 4,
    },
    {
        "id": "kernel-05-memory",
        "name": "Memory Kernel",
        "file": "05_memory_kernel.yaml",
        "purpose": "Memory substrate operations, retrieval strategies, context management",
        "priority": 5,
    },
    {
        "id": "kernel-06-worldmodel",
        "name": "World Model Kernel",
        "file": "06_worldmodel_kernel.yaml",
        "purpose": "Entity tracking, state management, world representation",
        "priority": 6,
    },
    {
        "id": "kernel-07-execution",
        "name": "Execution Kernel",
        "file": "07_execution_kernel.yaml",
        "purpose": "Tool orchestration, task execution, action dispatch",
        "priority": 7,
    },
    {
        "id": "kernel-08-safety",
        "name": "Safety Kernel",
        "file": "08_safety_kernel.yaml",
        "purpose": "Safety constraints, approval gates, destructive operation guards",
        "priority": 8,
        "is_safety_kernel": True,
    },
    {
        "id": "kernel-09-developer",
        "name": "Developer Kernel",
        "file": "09_developer_kernel.yaml",
        "purpose": "Code generation patterns, development workflows, best practices",
        "priority": 9,
    },
    {
        "id": "kernel-10-packet-protocol",
        "name": "Packet Protocol Kernel",
        "file": "10_packet_protocol_kernel.yaml",
        "purpose": "Memory packet structure, ingestion protocols, audit trail",
        "priority": 10,
    },
]

# High-risk tools that require SafetyKernel guard
# Note: Tool names must match OpenAI pattern ^[a-zA-Z0-9_-]+$ (no dots)
HIGH_RISK_TOOLS = [
    "gmp_run",
    "git_commit",
    "mac_agent_exec_task",
    "github_create_pull_request",
    "github_merge_pull_request",
    "vercel_trigger_deploy",
]


async def create_schema_constraints(driver: "AsyncDriver") -> int:
    """Create indexes and constraints for governance labels.
    
    Returns number of constraints created.
    """
    constraints = [
        # Unique ID constraints
        "CREATE CONSTRAINT responsibility_id IF NOT EXISTS FOR (r:Responsibility) REQUIRE r.id IS UNIQUE",
        "CREATE CONSTRAINT directive_id IF NOT EXISTS FOR (d:Directive) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT sop_id IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT kernel_id IF NOT EXISTS FOR (k:Kernel) REQUIRE k.id IS UNIQUE",
    ]
    
    created = 0
    async with driver.session() as session:
        for constraint in constraints:
            try:
                await session.run(constraint)
                created += 1
            except Exception as e:
                # Constraint may already exist
                if "already exists" not in str(e).lower():
                    logger.warning("constraint_creation_failed", constraint=constraint[:50], error=str(e))
    
    return created


async def create_governance_entities(driver: "AsyncDriver", agent_id: str = "L") -> dict:
    """Create governance entities for an agent.
    
    Returns dict with counts of created entities.
    """
    stats = {"responsibilities": 0, "directives": 0, "sops": 0, "relationships": 0}
    
    async with driver.session() as session:
        # Ensure agent exists
        await session.run(
            """
            MERGE (a:Agent {id: $agent_id})
            SET a.tenant_id = 'l-cto'
            """,
            {"agent_id": agent_id}
        )
        
        # Create Responsibilities
        for resp in L_RESPONSIBILITIES:
            result = await session.run(
                """
                MERGE (r:Responsibility {id: $id})
                SET r.name = $name,
                    r.description = $description,
                    r.priority = $priority,
                    r.tenant_id = 'l-cto'
                WITH r
                MATCH (a:Agent {id: $agent_id})
                MERGE (a)-[:HAS_RESPONSIBILITY]->(r)
                RETURN r.id
                """,
                {**resp, "agent_id": agent_id}
            )
            if await result.single():
                stats["responsibilities"] += 1
                stats["relationships"] += 1
        
        # Create Directives
        for directive in L_DIRECTIVES:
            result = await session.run(
                """
                MERGE (d:Directive {id: $id})
                SET d.name = $name,
                    d.description = $description,
                    d.enforced = $enforced,
                    d.tenant_id = 'l-cto'
                WITH d
                MATCH (a:Agent {id: $agent_id})
                MERGE (a)-[:HAS_DIRECTIVE]->(d)
                RETURN d.id
                """,
                {**directive, "agent_id": agent_id}
            )
            if await result.single():
                stats["directives"] += 1
                stats["relationships"] += 1
        
        # Create SOPs
        for sop in L_SOPS:
            result = await session.run(
                """
                MERGE (s:SOP {id: $id})
                SET s.name = $name,
                    s.description = $description,
                    s.doc_ref = $doc_ref,
                    s.tenant_id = 'l-cto'
                WITH s
                MATCH (a:Agent {id: $agent_id})
                MERGE (a)-[:HAS_SOP]->(s)
                RETURN s.id
                """,
                {**sop, "agent_id": agent_id}
            )
            if await result.single():
                stats["sops"] += 1
                stats["relationships"] += 1
    
    return stats


async def create_kernel_entities(driver: "AsyncDriver", agent_id: str = "L") -> dict:
    """Create Kernel nodes and GOVERNED_BY relationships.
    
    Creates nodes for each of the 10 governance kernels and links them to the agent.
    
    Returns dict with counts of created entities.
    """
    stats = {"kernels": 0, "governed_by": 0}
    
    async with driver.session() as session:
        for kernel in L_KERNELS:
            result = await session.run(
                """
                MERGE (k:Kernel {id: $id})
                SET k.name = $name,
                    k.file = $file,
                    k.purpose = $purpose,
                    k.priority = $priority,
                    k.is_safety_kernel = $is_safety,
                    k.tenant_id = 'l-cto'
                WITH k
                MATCH (a:Agent {id: $agent_id})
                MERGE (a)-[:GOVERNED_BY {priority: $priority}]->(k)
                RETURN k.id
                """,
                {
                    **kernel,
                    "is_safety": kernel.get("is_safety_kernel", False),
                    "agent_id": agent_id,
                }
            )
            if await result.single():
                stats["kernels"] += 1
                stats["governed_by"] += 1
    
    return stats


async def create_tool_safety_guards(driver: "AsyncDriver") -> dict:
    """Create GUARDED_BY relationships between high-risk tools and SafetyKernel.
    
    Links destructive/high-risk tools to the Safety Kernel for governance enforcement.
    
    Returns dict with count of relationships created.
    """
    stats = {"guarded_by": 0}
    
    async with driver.session() as session:
        for tool_id in HIGH_RISK_TOOLS:
            result = await session.run(
                """
                MATCH (t:Tool {id: $tool_id})
                MATCH (k:Kernel {id: 'kernel-08-safety'})
                MERGE (t)-[:GUARDED_BY {enforcement: 'STRICT', requires_approval: true}]->(k)
                RETURN t.id
                """,
                {"tool_id": tool_id}
            )
            if await result.single():
                stats["guarded_by"] += 1
    
    return stats


async def create_agent_hierarchy(driver: "AsyncDriver") -> dict:
    """Create agent hierarchy relationships (REPORTS_TO).
    
    Establishes the authority chain: L REPORTS_TO igor
    
    Returns dict with relationship counts.
    """
    stats = {"agents": 0, "reports_to": 0}
    
    async with driver.session() as session:
        # Ensure igor agent exists
        result = await session.run(
            """
            MERGE (igor:Agent {id: 'igor'})
            SET igor.designation = 'Principal',
                igor.role = 'Founder & Principal',
                igor.authority_level = 'SUPREME',
                igor.tenant_id = 'l-cto'
            RETURN igor.id
            """
        )
        if await result.single():
            stats["agents"] += 1
        
        # Create REPORTS_TO relationship
        result = await session.run(
            """
            MATCH (l:Agent {id: 'L'})
            MATCH (igor:Agent {id: 'igor'})
            MERGE (l)-[:REPORTS_TO]->(igor)
            RETURN l.id
            """
        )
        if await result.single():
            stats["reports_to"] += 1
    
    return stats


async def bootstrap_l_governance(driver: "AsyncDriver") -> dict:
    """Bootstrap L agent's complete governance graph.
    
    Creates:
    - Schema constraints/indexes (Responsibility, Directive, SOP, Kernel)
    - Responsibility entities + HAS_RESPONSIBILITY relationships
    - Directive entities + HAS_DIRECTIVE relationships
    - SOP entities + HAS_SOP relationships
    - Kernel entities + GOVERNED_BY relationships (10 kernels)
    - GUARDED_BY relationships (high-risk tools → Safety Kernel)
    - Agent hierarchy (L REPORTS_TO igor)
    
    Args:
        driver: Neo4j AsyncDriver instance
        
    Returns:
        Dict with creation statistics
    """
    logger.info("bootstrap_l_governance_start")
    
    try:
        # Create schema constraints
        constraints_created = await create_schema_constraints(driver)
        logger.info("neo4j_constraints_created", count=constraints_created)
        
        # Create L's governance entities (Responsibilities, Directives, SOPs)
        entity_stats = await create_governance_entities(driver, agent_id="L")
        logger.info(
            "neo4j_governance_entities_created",
            responsibilities=entity_stats["responsibilities"],
            directives=entity_stats["directives"],
            sops=entity_stats["sops"],
            relationships=entity_stats["relationships"],
        )
        
        # Create Kernel nodes and GOVERNED_BY relationships
        kernel_stats = await create_kernel_entities(driver, agent_id="L")
        logger.info(
            "neo4j_kernel_entities_created",
            kernels=kernel_stats["kernels"],
            governed_by=kernel_stats["governed_by"],
        )
        
        # Create GUARDED_BY relationships for high-risk tools
        guard_stats = await create_tool_safety_guards(driver)
        logger.info(
            "neo4j_tool_guards_created",
            guarded_by=guard_stats["guarded_by"],
        )
        
        # Create agent hierarchy (L REPORTS_TO igor)
        hierarchy_stats = await create_agent_hierarchy(driver)
        logger.info(
            "neo4j_hierarchy_created",
            agents=hierarchy_stats["agents"],
            reports_to=hierarchy_stats["reports_to"],
        )
        
        return {
            "success": True,
            "constraints_created": constraints_created,
            **entity_stats,
            "kernels": kernel_stats["kernels"],
            "governed_by": kernel_stats["governed_by"],
            "guarded_by": guard_stats["guarded_by"],
            "hierarchy_agents": hierarchy_stats["agents"],
            "reports_to": hierarchy_stats["reports_to"],
        }
        
    except Exception as e:
        logger.error("bootstrap_l_governance_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def main():
    """CLI entrypoint for standalone execution."""
    from neo4j import AsyncGraphDatabase, basic_auth
    
    uri = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    
    if not password:
        logger.info("ERROR: NEO4J_PASSWORD environment variable required")
        return
    
    logger.info(f"Connecting to Neo4j at {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=basic_auth(user, password))
    
    try:
        result = await bootstrap_l_governance(driver)
        logger.info(f"\nBootstrap Complete:")
        logger.info(f"  Constraints created: {result.get('constraints_created', 0)}")
        logger.info(f"  Responsibilities:    {result.get('responsibilities', 0)}")
        logger.info(f"  Directives:          {result.get('directives', 0)}")
        logger.info(f"  SOPs:                {result.get('sops', 0)}")
        logger.info(f"  Kernels:             {result.get('kernels', 0)}")
        logger.info(f"  GOVERNED_BY:         {result.get('governed_by', 0)}")
        logger.info(f"  GUARDED_BY:          {result.get('guarded_by', 0)}")
        logger.info(f"  REPORTS_TO:          {result.get('reports_to', 0)}")
        logger.info(f"  Other relationships: {result.get('relationships', 0)}")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

