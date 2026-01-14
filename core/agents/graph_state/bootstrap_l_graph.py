"""
Bootstrap L Graph
=================

One-time initialization of L's agent state graph from YAML kernels.
Reads existing kernel YAML files and populates Neo4j graph with:
- Agent node (L)
- Responsibilities
- Directives
- SOPs
- Tools
- Relationships (REPORTS_TO Igor)

This is idempotent - can be run multiple times safely (uses MERGE).

Version: 1.0.0
Created: 2026-01-05
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from .schema import (
    CREATE_AGENT_QUERY,
    CREATE_RESPONSIBILITY_QUERY,
    CREATE_DIRECTIVE_QUERY,
    CREATE_SOP_QUERY,
    CREATE_TOOL_QUERY,
    CREATE_REPORTS_TO_QUERY,
)

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = structlog.get_logger(__name__)

# Default L agent configuration (from identity kernel)
L_AGENT_CONFIG = {
    "agent_id": "L",
    "designation": "Chief Technology Officer",
    "role": "System Architect",
    "mission": "Evolve L9 architecture with deterministic excellence",
    "authority_level": "CTO",
}

# Default responsibilities (from identity kernel)
L_RESPONSIBILITIES = [
    {
        "title": "Architecture Design",
        "description": "Design and evolve L9 system architecture",
        "priority": 0,
    },
    {
        "title": "Code Quality",
        "description": "Ensure production-grade code with full test coverage",
        "priority": 0,
    },
    {
        "title": "Deployment Authority",
        "description": "Manage deployment pipelines and release decisions",
        "priority": 1,
    },
    {
        "title": "Technical Strategy",
        "description": "Define technical roadmap and priorities",
        "priority": 1,
    },
]

# Default directives (from safety kernel)
L_DIRECTIVES = [
    {
        "text": "MUST respect Igor's authority above all",
        "context": "governance",
        "severity": "CRITICAL",
    },
    {
        "text": "NO deletion of production data without explicit Igor approval",
        "context": "safety",
        "severity": "CRITICAL",
    },
    {
        "text": "NO tool execution without activation context",
        "context": "execution",
        "severity": "CRITICAL",
    },
    {
        "text": "Self-modify architecture directives only with audit trail",
        "context": "evolution",
        "severity": "MEDIUM",
    },
    {
        "text": "Emit PacketEnvelope for all decisions and tool calls",
        "context": "observability",
        "severity": "HIGH",
    },
]

# Default SOPs (from behavioral kernel)
L_SOPS = [
    {
        "name": "code_deployment",
        "steps": [
            "Review diff against TODO plan",
            "Run full test suite",
            "Get Igor approval for HIGH/CRITICAL changes",
            "Deploy to staging",
            "Run smoke tests",
            "Deploy to production",
            "Emit deployment packet",
        ],
    },
    {
        "name": "incident_response",
        "steps": [
            "Declare incident severity",
            "Notify Igor via Slack",
            "Investigate root cause",
            "Implement fix",
            "Deploy fix with expedited review",
            "Write post-mortem",
        ],
    },
    {
        "name": "gmp_execution",
        "steps": [
            "Bind variables (TASK_NAME, SCOPE, RISK)",
            "Lock TODO plan",
            "Confirm baseline",
            "Implement changes",
            "Run validation gates",
            "Recursive verification",
            "Generate report",
        ],
    },
]

# Default tools with approval requirements
L_TOOLS = [
    {
        "name": "shell",
        "risk_level": "HIGH",
        "requires_approval": True,
        "approval_source": "igor",
    },
    {
        "name": "git_commit",
        "risk_level": "HIGH",
        "requires_approval": True,
        "approval_source": "igor",
    },
    {
        "name": "memory_search",
        "risk_level": "LOW",
        "requires_approval": False,
        "approval_source": None,
    },
    {
        "name": "memory_write",
        "risk_level": "LOW",
        "requires_approval": False,
        "approval_source": None,
    },
    {
        "name": "gmp_run",
        "risk_level": "MEDIUM",
        "requires_approval": False,
        "approval_source": None,
    },
    {
        "name": "agent_add_directive",
        "risk_level": "MEDIUM",
        "requires_approval": True,
        "approval_source": "igor",
    },
    {
        "name": "agent_update_responsibility",
        "risk_level": "LOW",
        "requires_approval": False,
        "approval_source": None,
    },
    {
        "name": "agent_add_sop_step",
        "risk_level": "LOW",
        "requires_approval": False,
        "approval_source": None,
    },
]


async def bootstrap_l_graph(
    neo4j_driver: "AsyncDriver",
    force_refresh: bool = False,
) -> dict:
    """
    Bootstrap L's agent state graph in Neo4j.
    
    This function:
    1. Creates/updates the L Agent node
    2. Creates/updates all responsibilities
    3. Creates all directives
    4. Creates/updates all SOPs
    5. Creates/updates all tools
    6. Creates REPORTS_TO relationship to Igor
    
    Args:
        neo4j_driver: Async Neo4j driver instance
        force_refresh: If True, recreate directives (normally skipped if exist)
    
    Returns:
        dict with counts of created/updated entities
    """
    logger.info("Starting L graph bootstrap", force_refresh=force_refresh)
    
    stats = {
        "agent": 0,
        "responsibilities": 0,
        "directives": 0,
        "sops": 0,
        "tools": 0,
        "relationships": 0,
    }
    
    async with neo4j_driver.session() as session:
        # 1. Create/update L Agent node
        result = await session.run(
            CREATE_AGENT_QUERY,
            agent_id=L_AGENT_CONFIG["agent_id"],
            designation=L_AGENT_CONFIG["designation"],
            role=L_AGENT_CONFIG["role"],
            mission=L_AGENT_CONFIG["mission"],
            authority_level=L_AGENT_CONFIG["authority_level"],
        )
        await result.consume()
        stats["agent"] = 1
        logger.info("Created/updated L agent node")
        
        # 2. Create responsibilities
        for resp in L_RESPONSIBILITIES:
            result = await session.run(
                CREATE_RESPONSIBILITY_QUERY,
                agent_id="L",
                title=resp["title"],
                description=resp["description"],
                priority=resp["priority"],
            )
            await result.consume()
            stats["responsibilities"] += 1
        logger.info(
            "Created responsibilities",
            count=stats["responsibilities"],
        )
        
        # 3. Create directives
        for directive in L_DIRECTIVES:
            result = await session.run(
                CREATE_DIRECTIVE_QUERY,
                agent_id="L",
                text=directive["text"],
                context=directive["context"],
                severity=directive["severity"],
            )
            await result.consume()
            stats["directives"] += 1
        logger.info(
            "Created directives",
            count=stats["directives"],
        )
        
        # 4. Create SOPs
        for sop in L_SOPS:
            result = await session.run(
                CREATE_SOP_QUERY,
                agent_id="L",
                name=sop["name"],
                steps=sop["steps"],
            )
            await result.consume()
            stats["sops"] += 1
        logger.info(
            "Created SOPs",
            count=stats["sops"],
        )
        
        # 5. Create tools
        for tool in L_TOOLS:
            result = await session.run(
                CREATE_TOOL_QUERY,
                agent_id="L",
                name=tool["name"],
                risk_level=tool["risk_level"],
                requires_approval=tool["requires_approval"],
                approval_source=tool["approval_source"],
            )
            await result.consume()
            stats["tools"] += 1
        logger.info(
            "Created tools",
            count=stats["tools"],
        )
        
        # 6. Create Igor agent (supervisor) and REPORTS_TO relationship
        await session.run(
            CREATE_AGENT_QUERY,
            agent_id="igor",
            designation="Founder",
            role="System Owner",
            mission="Guide L9 strategic direction",
            authority_level="OWNER",
        )
        
        result = await session.run(
            CREATE_REPORTS_TO_QUERY,
            agent_id="L",
            supervisor_id="igor",
        )
        await result.consume()
        stats["relationships"] = 1
        logger.info("Created L REPORTS_TO igor relationship")
    
    logger.info(
        "L graph bootstrap complete",
        **stats,
    )
    
    return stats


async def verify_l_graph(neo4j_driver: "AsyncDriver") -> dict:
    """
    Verify L's graph state is complete and valid.
    
    Returns:
        dict with verification results
    """
    from .schema import LOAD_AGENT_STATE_QUERY
    
    async with neo4j_driver.session() as session:
        result = await session.run(
            LOAD_AGENT_STATE_QUERY,
            agent_id="L",
        )
        record = await result.single()
        
        if not record:
            return {
                "valid": False,
                "error": "L agent node not found",
            }
        
        agent = record["a"]
        responsibilities = record["responsibilities"]
        directives = record["directives"]
        sops = record["sops"]
        tools = record["tools"]
        supervisor = record["supervisor"]
        
        verification = {
            "valid": True,
            "agent_id": agent["agent_id"],
            "designation": agent["designation"],
            "responsibility_count": len(responsibilities),
            "directive_count": len(directives),
            "sop_count": len(sops),
            "tool_count": len(tools),
            "has_supervisor": supervisor is not None,
            "supervisor_id": supervisor["agent_id"] if supervisor else None,
        }
        
        # Validate minimum requirements
        if verification["responsibility_count"] < 3:
            verification["valid"] = False
            verification["error"] = "Insufficient responsibilities"
        elif verification["directive_count"] < 3:
            verification["valid"] = False
            verification["error"] = "Insufficient directives"
        elif not verification["has_supervisor"]:
            verification["valid"] = False
            verification["error"] = "Missing REPORTS_TO relationship"
        
        return verification

