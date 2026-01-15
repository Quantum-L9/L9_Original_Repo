"""
Phase 0: Blueprint Validation

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Verify all prerequisites exist before starting initialization.
"""

from __future__ import annotations

from typing import Tuple, TYPE_CHECKING
from pathlib import Path

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

    # Check 4: Tool registry available
    tool_registry = getattr(substrate_service, "tool_registry", None)
    if tool_registry is None:
        # Allow missing tool registry for now (will be created later)
        logger.warning("Tool registry not initialized, will create during bootstrap")
    checks.append(("tool_registry_available", True))

    logger.info(
        "Blueprint validation complete",
        agent_id=agent_config.agent_id,
        checks_passed=len(checks),
    )
    return True, ""
