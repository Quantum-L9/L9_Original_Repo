"""
L9 Dependency Injection Package
===============================

Lightweight DI framework following Dependency Inversion Principle.

Exports:
- DIContainer: Main container for dependency registration and resolution
- get_di_container: Get global container instance
- reset_di_container: Reset global container (testing)
- Error classes for handling resolution failures

Usage:
    from core.di import DIContainer, get_di_container
    from core.protocols import CacheClient

    container = get_di_container()
    container.bind_singleton(CacheClient, lambda: RedisClient())
    cache = container.resolve(CacheClient)

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from core.di.container import (
    BindingNotFoundError,
    CircularDependencyError,
    DIContainer,
    DIContainerError,
    MemorySubstrateContainer,
    ResolutionError,
    get_di_container,
    reset_di_container,
)

__all__ = [
    "BindingNotFoundError",
    "CircularDependencyError",
    "DIContainer",
    "DIContainerError",
    "MemorySubstrateContainer",
    "ResolutionError",
    "get_di_container",
    "reset_di_container",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-046",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.di.container"],
    "tags": ["caching", "core", "foundation", "testing", "utility"],
    "keywords": [
        "cache",
        "cacheclient",
        "container",
        "core",
        "dependency",
        "dicontainer",
        "global",
        "resolution",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:46Z",
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
