"""
10_packet_protocol_kernel → WS Router / Task Routing / EventStream

In orchestration/ws_task_router.py, runtime/websocket_orchestrator.py, or EventStream layer.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Protocol Wiring",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "packet_protocol_wiring",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.integration.test_kernel_router_orchestrator_end_to_end"],
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


def get_packet_protocol() -> dict:
    return _get_kernels().get_kernel("packet_protocol") or {}


def get_allowed_event_types() -> list:
    return (
        _get_kernels().get_rule("packet_protocol", "events.allowed_types", default=[])
        or []
    )


def get_default_channel() -> str:
    return _get_kernels().get_rule(
        "packet_protocol", "routing.default_channel", default="agent"
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.kernel_loader"],
    "tags": ["core", "event-driven", "foundation", "realtime", "streaming", "utility"],
    "keywords": [
        "allowed",
        "channel",
        "default",
        "event",
        "eventstream",
        "packet",
        "protocol",
        "router",
    ],
    "business_value": "Utility module for packet protocol wiring",
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
