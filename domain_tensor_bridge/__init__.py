#!/usr/bin/env python3
"""
================================================================================
Module: Domain-Tensor Bridge
Purpose: Central orchestrator connecting domain data with TensorAIOS layer
================================================================================

Summary:
    L9 Domain-Tensor Bridge v6.0 is the OS-level cognitive orchestrator that
    bridges domain-specific business logic with neural-symbolic reasoning.
    It manages packet routing, context enrichment, multi-modal reasoning,
    governance feedback, and learning loops.

Extended Metadata:
    See __footer_meta__ at module footer. Runtime trace in __l9_trace__.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: OPS-DTB-001
# layer: operations
# domain: agent_orchestration
# governance_level: critical
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-31T22:21:51Z",
    "layer": "operations",
    "domain": "domain_tensor_bridge",
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

from .agent_controller import AgentController, process_packet
from .decision_synthesizer import DecisionSynthesizer
from .governance_bridge import GovernanceBridge
from .memory_bridge import MemoryBridge
from .packet_router import PacketRouter
from .reasoning_engine import ReasoningEngine

__version__ = "6.0.0"

# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================

__footer_meta__ = {
    "component_id": "OPS-DTB-001",
    "component_name": "Domain-Tensor Bridge",
    "module_version": "6.0.0",
    "created_at": "2026-01-02T03:35:00Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "operations",
    "domain": "agent_orchestration",
    "type": "service",
    "status": "active",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Central orchestrator connecting domain data with TensorAIOS layer",
    "summary": "OS-level cognitive orchestrator bridging domain-specific business logic with neural-symbolic reasoning. Manages packet routing, context enrichment, multi-modal reasoning, governance feedback, and learning loops.",
    "dependencies": [
        "l9.core.schemas",
        "l9.core.governance",
        "l9.memory.substrate_service",
    ],
}

__all__ = [
    "AgentController",
    "DecisionSynthesizer",
    "GovernanceBridge",
    "MemoryBridge",
    "PacketRouter",
    "ReasoningEngine",
    "__footer_meta__",
    "__l9_trace__",
    "__version__",
    "process_packet",
]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
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
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "DOM-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["domain-tensor-bridge", "operations", "tracing", "utility"],
    "keywords": [],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:51Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
