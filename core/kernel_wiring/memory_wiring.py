"""
05_memory_kernel → Memory Adapter / Substrate Client

In memory/memory_client.py or similar.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Wiring",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "memory_wiring",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
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


def get_memory_layers_config() -> dict:
    """Returns the configuration dictionary for memory layers from kernel rules, used in memory adapter setup."""
    return _get_kernels().get_rule("memory", "layers", default={}) or {}


def should_checkpoint_now(event_type: str) -> bool:
    """
    Checks if the given event type should trigger a memory checkpoint based on configured rules.

    Args:
        event_type: The type of event to evaluate against checkpointing triggers.

    Returns:
        True if the event type matches a checkpointing trigger; otherwise, False.
    """
    rules = (
        _get_kernels().get_rule("memory", "checkpointing.triggers", default=[]) or []
    )
    return event_type in rules


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.kernel_loader"],
    "tags": ["adapter", "core", "event-driven", "foundation"],
    "keywords": [
        "checkpoint",
        "layers",
        "memory",
        "now",
        "should",
        "substrate",
        "wiring",
    ],
    "business_value": "Utility module for memory wiring",
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
