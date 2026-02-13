"""
Runtime Governance Layer: Enforce law at execution time.

Provides:
- Enforcement engine: Apply rules to operations
- CA router: Route coding agent requests through gates
- Escalation: Bubble up to L when needed
"""

__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T03:51:59.750577+00:00",
    "updated_at": "2026-02-13T03:51:59.750577+00:00",
    "layer": "foundation",
    "domain": "runtime",
    "module_name": "codegen.dev_layer.runtime.__init__",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


from dev_layer.runtime import enforcement

__all__ = ["enforcement"]
