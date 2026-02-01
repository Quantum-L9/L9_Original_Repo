"""
L9 Core Boundary Module
=======================

PRIVATE_BOUNDARY enforcement at the orchestrator edge.

Provides:
- Boundary specification loading and parsing
- Prompt/response enforcement (redaction)
- Payload field protection

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.boundary.enforcer import (  # Functions; Classes; Constants
    BOUNDARY_FILE,
    BoundaryEnforcer,
    BoundarySpec,
    enforce_boundary,
    enforce_payload_boundary,
    enforce_response_boundary,
    get_default_enforcer,
    load_boundary_spec,
    parse_boundary_spec,
)

__all__ = [
    # Constants
    "BOUNDARY_FILE",
    "BoundaryEnforcer",
    # Classes
    "BoundarySpec",
    "enforce_boundary",
    "enforce_payload_boundary",
    "enforce_response_boundary",
    "get_default_enforcer",
    # Functions
    "load_boundary_spec",
    "parse_boundary_spec",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-081",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.boundary.enforcer"],
    "tags": ["core", "foundation", "utility"],
    "keywords": ["boundary", "enforcement", "module", "orchestrator"],
    "business_value": "Boundary specification loading and parsing Prompt/response enforcement (redaction) Payload field protection Version: 1.0.0",
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
