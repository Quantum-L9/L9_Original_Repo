"""
TensorGlobe Bridge Adapter

External cognitive accelerator adapter for L9.
Gated by EOS + Accountability. Read-only. Evidence-producing.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:55Z",
    "layer": "operations",
    "domain": "adapters",
    "module_name": "__init__",
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

from .adapter import TensorGlobeBridgeAdapter
from .schemas import (
    AnomalySignal,
    TensorOperation,
    TensorRequest,
    TensorRequestPacket,
    TensorResponse,
    TensorResponsePacket,
    TensorResult,
)

__all__ = [
    "AnomalySignal",
    "TensorGlobeBridgeAdapter",
    "TensorOperation",
    "TensorRequest",
    "TensorRequestPacket",
    "TensorResponse",
    "TensorResponsePacket",
    "TensorResult",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ADA-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "adapters", "operations"],
    "keywords": ["adapter"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:55Z",
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
