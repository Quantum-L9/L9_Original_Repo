"""
07_execution_kernel → Execution Engine / State Machine

In your execution engine module (or where you plan to put it).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Execution Wiring",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "execution_wiring",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.runtime.test_execution_wiring_sanity"],
    },
}
# ============================================================================

_KERNELS = None

def _get_kernels():
    """Lazy load kernel stack."""
    global _KERNELS
    if _KERNELS is None:
        from runtime.kernel_loader import load_kernel_stack

        _KERNELS = load_kernel_stack()
    return _KERNELS

def get_execution_state_machine() -> dict:
    return _get_kernels().get_kernel("execution") or {}

def get_allowed_transitions(state: str) -> list:
    sm = get_execution_state_machine()
    transitions = sm.get("transitions", {})
    return transitions.get(state, [])

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.kernel_loader"],
    "tags": ["core", "foundation", "utility"],
    "keywords": ["allowed", "engine", "execution", "machine", "module", "state", "transitions", "wiring"],
    "business_value": "Utility module for execution wiring",
    "last_modified": "2026-01-07T13:35:57Z",
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
