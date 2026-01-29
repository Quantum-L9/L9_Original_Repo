"""
L9 Core - Module Registry
========================

Runtime registry for "what modules exist, what they expose, and whether they're active/healthy".

This is NOT the YAML `specs/MODULE_REGISTRY.yaml` (which is a design/spec artifact).
This registry is runtime truth derived from server wiring and health checks.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Module Registry",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T01:22:11Z",
    "updated_at": "2026-01-08T22:15:53Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "moduleregistry",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.routes.modules", "api.server"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ModuleDefinition:
    """Immutable definition of a registered module.

    Attributes:
        module_id: Unique identifier for the module.
        display_name: Human-readable name for display.
        route_prefix: API route prefix (e.g., /api/v1/memory).
        owner: Team or person responsible for the module.
        version: Semantic version string.
        required_env: Tuple of required environment variable names.
    """

    module_id: str
    display_name: str
    route_prefix: str | None = None
    owner: str | None = None
    version: str | None = None
    required_env: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModuleStatus:
    """Immutable runtime status of a registered module.

    Attributes:
        module_id: Unique identifier for the module.
        enabled: Whether the module is enabled in configuration.
        available: Whether the module's dependencies are available.
        initialized: Whether the module has been successfully initialized.
        notes: Optional status notes or error messages.
        metadata: Additional status metadata.
    """

    module_id: str
    enabled: bool
    available: bool
    initialized: bool
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ModuleRegistry:
    """
    In-memory module registry (runtime truth).

    - register(): declare module existence (and metadata)
    - set_status(): update current runtime status
    - snapshot(): deterministic, JSON-ready view
    """

    def __init__(self) -> None:
        """Initialize an empty module registry."""
        self._definitions: dict[str, ModuleDefinition] = {}
        self._status: dict[str, ModuleStatus] = {}
        logger.info("ModuleRegistry initialized")

    def register(self, definition: ModuleDefinition) -> None:
        """Register a module definition.

        Args:
            definition: Module definition to register.
        """
        self._definitions[definition.module_id] = definition

    def set_status(self, status: ModuleStatus) -> None:
        """Update the runtime status of a module.

        Args:
            status: Module status to set.
        """
        self._status[status.module_id] = status

    def get_definition(self, module_id: str) -> ModuleDefinition | None:
        """Get the definition for a module.

        Args:
            module_id: Unique module identifier.

        Returns:
            ModuleDefinition if found, None otherwise.
        """
        return self._definitions.get(module_id)

    def get_status(self, module_id: str) -> ModuleStatus | None:
        """Get the runtime status for a module.

        Args:
            module_id: Unique module identifier.

        Returns:
            ModuleStatus if found, None otherwise.
        """
        return self._status.get(module_id)

    def snapshot(self) -> dict[str, Any]:
        """
        Return a deterministic snapshot (sorted by module_id).
        """
        module_ids = sorted(set(self._definitions.keys()) | set(self._status.keys()))
        modules: list[dict[str, Any]] = []

        for module_id in module_ids:
            definition = self._definitions.get(module_id)
            status = self._status.get(module_id)

            modules.append(
                {
                    "module_id": module_id,
                    "definition": (
                        None
                        if definition is None
                        else {
                            "display_name": definition.display_name,
                            "route_prefix": definition.route_prefix,
                            "owner": definition.owner,
                            "version": definition.version,
                            "required_env": list(definition.required_env),
                        }
                    ),
                    "status": (
                        None
                        if status is None
                        else {
                            "enabled": status.enabled,
                            "available": status.available,
                            "initialized": status.initialized,
                            "notes": status.notes,
                            "metadata": status.metadata,
                        }
                    ),
                }
            )

        return {"count": len(modules), "modules": modules}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "dataclass", "foundation", "logging"],
    "keywords": [
        "definition",
        "module",
        "register",
        "registry",
        "runtime",
        "snapshot",
        "status",
        "they",
    ],
    "business_value": "This is NOT the YAML `specs/MODULE_REGISTRY.yaml` (which is a design/spec artifact).",
    "last_modified": "2026-01-08T22:15:53Z",
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
