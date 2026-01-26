"""
L9 Core Governance - Policy Auto-Discovery System
=================================================

Automatic discovery and registration of governance policies.

This module enhances the existing PolicyLoader with auto-discovery
capabilities and better observability.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Policy Registry",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "core",
    "domain": "governance",
    "module_name": "policy_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.governance.engine"],
    },
}
# ============================================================================

from dataclasses import dataclass
from pathlib import Path

import structlog

from core.auto_registry import AutoRegistry
from core.governance.schemas import Policy

logger = structlog.get_logger(__name__)


# =============================================================================
# Policy Source Configuration
# =============================================================================


@dataclass
class PolicySource:
    """Configuration for a governance policy source."""

    name: str
    path: Path
    description: str = ""
    enabled: bool = True
    priority: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
        }


# =============================================================================
# Governance Policy Registry
# =============================================================================


def _validate_policy_source(source: PolicySource) -> bool:
    """Validate that an object is a valid policy source."""
    return isinstance(source, PolicySource) and source.path.exists()


# Global governance policy source registry
policy_source_registry = AutoRegistry[PolicySource](
    name="governance_policy_sources",
    validator=_validate_policy_source,
    allow_duplicates=False,
)


def register_policy_source(
    name: str,
    path: str | Path,
    description: str = "",
    enabled: bool = True,
    priority: int = 0,
):
    """
    Register a governance policy source directory.

    Args:
        name: Human-readable name for the policy source
        path: Path to the directory containing policy YAML files
        description: Description of the policy source
        enabled: Whether this source is enabled
        priority: Loading priority (higher = loaded first)

    Example:
        register_policy_source(
            name="core_policies",
            path="core/governance/policies",
            description="Core L9 governance policies",
            priority=100
        )
    """
    source = PolicySource(
        name=name,
        path=Path(path),
        description=description,
        enabled=enabled,
        priority=priority,
    )

    policy_source_registry.register_instance(
        component_id=name, component=source, priority=priority
    )

    logger.info("policy_source_registry.registered", name=name, path=str(path))


def discover_policy_sources() -> list[PolicySource]:
    """
    Get all registered policy sources, sorted by priority.

    Returns:
        List of PolicySource objects, sorted by priority (highest first)
    """
    policy_source_registry.initialize_factories()

    sources: list[PolicySource] = []

    for source_id in policy_source_registry.list_ids():
        source = policy_source_registry.get(source_id)
        if source and source.enabled:
            sources.append(source)

    # Sort by priority (highest first)
    sources.sort(key=lambda s: s.priority, reverse=True)

    logger.info("policy_source_registry.sources_retrieved", count=len(sources))
    return sources


def get_all_policy_sources() -> dict[str, PolicySource]:
    """
    Get all registered policy sources as a dictionary.

    Returns:
        Dictionary mapping source names to PolicySource objects
    """
    policy_source_registry.initialize_factories()

    sources: dict[str, PolicySource] = {}

    for source_id in policy_source_registry.list_ids():
        source = policy_source_registry.get(source_id)
        if source:
            sources[source_id] = source

    return sources


def load_policies_from_sources() -> list[Policy]:
    """
    Load all policies from registered sources.

    Returns:
        List of Policy objects loaded from all sources

    Example:
        from core.governance.policy_registry import (
            register_policy_source,
            load_policies_from_sources
        )

        # Register sources
        register_policy_source("core", "core/governance/policies", priority=100)
        register_policy_source("plugins", "plugins/policies", priority=50)

        # Load all policies
        policies = load_policies_from_sources()
    """
    from core.governance.loader import PolicyLoader

    sources = discover_policy_sources()
    all_policies: list[Policy] = []

    for source in sources:
        logger.info(
            "policy_source_registry.loading_from_source",
            name=source.name,
            path=str(source.path),
        )

        loader = PolicyLoader()
        try:
            loader.load_from_directory(str(source.path))
            all_policies.extend(loader.policies)
            logger.info(
                "policy_source_registry.loaded_from_source",
                name=source.name,
                count=loader.policy_count,
            )
        except Exception as e:
            logger.error(
                "policy_source_registry.load_failed",
                name=source.name,
                path=str(source.path),
                error=str(e),
            )

    logger.info("policy_source_registry.all_policies_loaded", total=len(all_policies))
    return all_policies


def get_policy_source_snapshot() -> dict:
    """Get a snapshot of all registered policy sources for observability."""
    return policy_source_registry.snapshot()


def register_default_policy_sources() -> int:
    """
    Bridge function: Register default policy source directories.

    This allows existing policy YAML files to be discovered by the new
    auto-registration system.

    Returns:
        Number of policy sources registered
    """
    from pathlib import Path

    registered = 0

    # Find project root (where config/ is located)
    # Go up from core/governance to project root
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent

    # Default policy directories
    policy_dirs = [
        (
            project_root / "config" / "policies",
            "config_policies",
            "Core configuration policies",
        ),
        (
            project_root / "private" / "policies",
            "private_policies",
            "Private/sensitive policies",
        ),
    ]

    for policy_path, source_name, description in policy_dirs:
        if policy_path.exists() and policy_path.is_dir():
            try:
                register_policy_source(
                    name=source_name,
                    path=policy_path,
                    description=description,
                    priority=10 if "config" in source_name else 5,
                    enabled=True,
                )
                registered += 1
                logger.info(
                    "legacy_policy_source_registered",
                    name=source_name,
                    path=str(policy_path),
                )
            except Exception as e:
                logger.debug(
                    "legacy_policy_source_skip", name=source_name, error=str(e)
                )

    if registered > 0:
        logger.info("legacy_policy_sources_registered", count=registered)

    return registered


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-GOV-POLICY-REG",
    "governance_level": "critical",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
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
