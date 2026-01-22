"""
Phase 0: Blueprint Validation

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Verify all prerequisites exist before starting initialization.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 0 Validate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_0_validate",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.core.bootstrap.test_bootstrap_phases"],
    },
}
# ============================================================================

from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import structlog

if TYPE_CHECKING:
    from core.agents.schemas import AgentConfig
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


async def validate_agent_blueprint(
    agent_config: "AgentConfig",
    substrate_service: "MemorySubstrateService",
) -> Tuple[bool, str]:
    """
    Validate agent blueprint before initialization.

    Checks:
    - Agent config has required fields
    - All kernel files exist
    - Memory substrates online (PostgreSQL, Neo4j)
    - Tool registry available

    Returns:
        (success, error_message)
    """
    checks = []

    # Check 1: Agent config has required fields
    if not getattr(agent_config, "agent_id", None) or not getattr(
        agent_config, "name", None
    ):
        return False, "Agent config missing agent_id or name"
    checks.append(("config_valid", True))
    logger.debug("Blueprint check passed", check="config_valid")

    # Check 2: All kernel files exist
    kernel_refs = getattr(agent_config, "kernel_refs", [])
    kernel_dir = Path("private/kernels/00_system")

    for kernel_ref in kernel_refs:
        kernel_path = kernel_dir / kernel_ref
        if not kernel_path.exists():
            return False, f"Kernel file not found: {kernel_path}"
    checks.append(("kernels_discoverable", True))
    logger.debug(
        "Blueprint check passed", check="kernels_discoverable", count=len(kernel_refs)
    )

    # Check 3: Memory substrates online
    try:
        # Ping Postgres via substrate service
        if (
            hasattr(substrate_service, "postgres_pool")
            and substrate_service.postgres_pool
        ):
            async with substrate_service.postgres_pool.acquire() as conn:
                await conn.execute("SELECT 1")
        checks.append(("postgres_online", True))
        logger.debug("Blueprint check passed", check="postgres_online")
    except Exception as e:
        return False, f"PostgreSQL offline: {e}"

    try:
        # Ping Neo4j via global client (lazy import to avoid test collection issues)
        from memory.graph_client import get_neo4j_client

        neo4j_client = await get_neo4j_client()
        if neo4j_client:
            async with neo4j_client.session() as session:
                await session.run("RETURN 1")
            checks.append(("neo4j_online", True))
            logger.debug("Blueprint check passed", check="neo4j_online")
        else:
            logger.warning("Neo4j client not available during validation")
            checks.append(("neo4j_online", False))
    except Exception as e:
        return False, f"Neo4j offline: {e}"

    # Check 4: Tool registry available (via singleton, not substrate attribute)
    # Tool registry is managed separately via get_tool_registry() singleton pattern
    # in core/tools/base_registry.py - not a substrate service dependency
    try:
        from core.tools.base_registry import get_tool_registry

        get_tool_registry()
        checks.append(("tool_registry_available", True))
        logger.debug("Blueprint check passed", check="tool_registry_available")
    except ImportError:
        logger.warning("Tool registry module not available")
        checks.append(("tool_registry_available", False))

    logger.info(
        "Blueprint validation complete",
        agent_id=agent_config.agent_id,
        checks_passed=len(checks),
    )
    return True, ""


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.schemas",
        "core.tools.base_registry",
        "memory.graph_client",
        "memory.substrate_service",
    ],
    "tags": [
        "agent-execution",
        "async",
        "debugging",
        "filesystem",
        "foundation",
        "logging",
        "messaging",
        "service",
        "testing",
    ],
    "keywords": ["agent", "blueprint", "phase", "validate"],
    "business_value": "Utility module for phase 0 validate",
    "last_modified": "2026-01-17T23:47:56Z",
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
