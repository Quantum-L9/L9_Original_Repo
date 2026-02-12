"""
Tool Package Registry
=====================

Explicit registry of all tool packages for auto-discovery.
Replaces magic package scanning with deterministic imports.

This is the central configuration for which modules contain
@register_tool decorated functions that should be discovered
during application startup.

Version: 1.1.0 (GMP-TS-META: Added tool_search_meta)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Package Registry",
    "module_version": "1.1.0",
    "created_by": "GMP-122",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-02-12T18:24:00Z",
    "layer": "runtime",
    "domain": "tools",
    "module_name": "tool_packages",
    "type": "config",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.tool_registry", "api.server"],
    },
}
# ============================================================================

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# TOOL PACKAGES REGISTRY
# =============================================================================
# All packages containing @register_tool decorated functions.
# Order determines discovery priority (first match wins for duplicate names).
#
# Migration Status:
# - [x] runtime.redis_tools (13 tools) - GMP-122
# - [x] runtime.mcp_tools (7 tools) - GMP-123
# - [x] runtime.tool_search_meta (1 tool) - GMP-TS-META (NEW)
# - [ ] runtime.slack_tools (3 tools) - pending
# - [ ] runtime.llm_tools (3 tools) - pending
# - [ ] runtime.governance_tools (4 tools) - pending
# - [ ] runtime.execution_tools (3 tools) - pending
# - [ ] runtime.memory_tools (18 tools) - pending
# - [ ] core.tools.introspection_tools (11 tools) - pending
# - [ ] core.tools.neo4j_tools (3 tools) - pending
# - [ ] core.tools.simulation_tools (3 tools) - pending
# - [ ] core.tools.kernel_tools (3 tools) - pending
# - [ ] core.worldmodel.tools (10 tools) - pending
# =============================================================================

TOOL_PACKAGES: list[str] = [
    # === META-TOOLS (Anthropic Pattern) ===
    "runtime.tool_search_meta",  # GMP-TS-META: tool_search meta-tool (1)
    # === MIGRATED (from l_tools.py) ===
    # "runtime.redis_tools",  # GMP-122: DISABLED - not needed per Igor
    "runtime.mcp_tools",  # GMP-123: MCP server tools (7)
    # === EXISTING (already use @register_tool) ===
    "core.tools.research_tools",  # Research tools (4)
    "core.tools.reflection_tools",  # Reflection tools (5)
    # === LEGACY (still in l_tools.py - to be migrated) ===
    # These will be added as modules are created:
    # "runtime.slack_tools",
    # "runtime.llm_tools",
    # "runtime.governance_tools",
    # "runtime.execution_tools",
    # "runtime.memory_tools",
    # "core.tools.introspection_tools",
    # "core.tools.neo4j_tools",
    # "core.tools.simulation_tools",
    # "core.tools.kernel_tools",
    # "core.worldmodel.tools",
]


def get_tool_packages() -> list[str]:
    """
    Get list of all tool packages to discover.

    Returns:
        Copy of the TOOL_PACKAGES list (to prevent mutation)
    """
    return TOOL_PACKAGES.copy()


def register_tool_package(package: str) -> bool:
    """
    Register a new tool package at runtime.

    Args:
        package: Fully qualified package name (e.g., "myapp.tools")

    Returns:
        True if added, False if already registered
    """
    if package in TOOL_PACKAGES:
        logger.debug("tool_package_already_registered", package=package)
        return False

    TOOL_PACKAGES.append(package)
    logger.info("tool_package_registered", package=package)
    return True


def discover_from_packages() -> int:
    """
    Trigger discovery of tools from all registered packages.

    This function imports each package in TOOL_PACKAGES,
    which causes their @register_tool decorators to execute
    and register tools with the tool_executor_registry.

    Skips packages already imported (avoids duplicate registration).

    Returns:
        Number of packages successfully imported
    """
    import sys

    from core.auto_registry import DuplicateRegistrationError
    from runtime.tool_registry import tool_executor_registry

    imported = 0
    skipped = 0
    for package in TOOL_PACKAGES:
        # Skip if already imported (tools already registered via decorator)
        if package in sys.modules:
            logger.debug("tool_package_already_imported", package=package)
            skipped += 1
            continue

        try:
            count = tool_executor_registry.discover(package, recursive=False)
            logger.info("tool_package_discovered", package=package, tools=count)
            imported += 1
        except ImportError as e:
            logger.warning("tool_package_import_failed", package=package, error=str(e))
        except DuplicateRegistrationError as e:
            # Tools already registered from this package (race condition or re-import)
            logger.debug(
                "tool_package_already_registered", package=package, error=str(e)
            )
            skipped += 1

    logger.info(
        "tool_packages_discovery_complete",
        packages_imported=imported,
        packages_skipped=skipped,
        total_packages=len(TOOL_PACKAGES),
    )
    return imported


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED
# =============================================================================
__dora_footer__ = {
    "component_id": "RUN-TOOL-PKG-001",
    "governance_level": "standard",
    "security_reviewed": False,
    "performance_tested": False,
    "last_audit": "2026-02-12T18:24:00Z",
}
# =============================================================================
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
