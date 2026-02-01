"""L9 Kernel - Core Orchestration & Packet Protocol.

Bounded Context: Kernel
Domain: Central orchestration, packet envelope protocol, routing.
Owner: L (CTO)

Kernel is responsible for:
  1. PacketEnvelope protocol (immutable, validated packets)
  2. Request routing to substrates
  3. Response aggregation
  4. Cross-cutting concerns (correlation IDs, tracing)

Kernel MUST NOT directly depend on:
  - Individual substrates beyond abstract interfaces
  - Business logic (that's in bounded contexts)
  - Configuration (use control_plane.config)

Kernel defines the contract that all substrates must implement.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Core Orchestration & Packet Protocol.",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T05:32:34Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from kernel.orchestrator import Orchestrator, OrchestratorConfig
from kernel.protocol import PacketEnvelope, PacketEnvelopeV2

__all__ = [
    "Orchestrator",
    "OrchestratorConfig",
    "PacketEnvelope",
    "PacketEnvelopeV2",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-023",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["integration", "mcp-integration", "utility"],
    "keywords": [
        "bounded",
        "core",
        "kernel",
        "must",
        "orchestration",
        "packet",
        "protocol",
        "protocol.",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:56Z",
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
