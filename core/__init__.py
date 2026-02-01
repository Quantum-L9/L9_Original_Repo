"""
L9 Core Module
==============

Core infrastructure for L9 orchestration system.

Submodules:
- abstractions: Protocol definitions for DI (kernel, memory, agent, observability)
- di: Dependency injection container and utilities
- schemas: Pydantic models for packets, research, security
- retrievers: Memory substrate retrievers
- kernels: Kernel integrity and loading
- boundary: PRIVATE_BOUNDARY enforcement
- gmp: GMP v2.0 meta-learning system (L2→L5 autonomy)

Version: 2.3.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "2.3.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

# Note: Submodules are imported on-demand to avoid circular imports
# Use explicit imports:
#   from core.schemas import PacketEnvelope
#   from core.kernels import check_kernel_integrity
#   from core.boundary import enforce_boundary

__version__ = "2.2.0"

# GMP v2.0 meta-learning system (lazy import to avoid circular deps)
# Usage: from core.gmp import GMPMetaLearningEngine, AutonomyController
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-004",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "foundation", "schema"],
    "keywords": [
        "agent",
        "core",
        "kernel",
        "memory",
        "module",
        "retrievers",
        "substrate",
        "system",
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
