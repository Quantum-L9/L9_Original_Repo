"""
L9 ADR (Architecture Decision Records) Tooling

This package provides CLI tools for managing ADRs in the L9 repository.

Usage:
    python -m tools.adr new "Use Protocol Buffers for IPC"
    python -m tools.adr list
    python -m tools.adr show 0042
    python -m tools.adr validate
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade Bot",
    "created_at": "2026-01-20T16:11:53Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
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

from tools.adr.adr_cli import main

__all__ = ["main"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "tools", "utility"],
    "keywords": ["python", "repository", "tools"],
    "business_value": "This package provides CLI tools for managing ADRs in the L9 repository. python -m tools.adr new "Use Protocol Buffers for IPC" python -m tools.adr list python -m tools.adr show 0042 python -m tools.ad",
    "last_modified": "2026-01-31T22:21:45Z",
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
