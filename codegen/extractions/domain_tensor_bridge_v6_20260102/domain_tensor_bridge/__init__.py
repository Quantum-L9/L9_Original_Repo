#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from .agent_controller import process_packet, AgentController
from .reasoning_engine import ReasoningEngine
from .decision_synthesizer import DecisionSynthesizer
from .packet_router import PacketRouter
from .governance_bridge import GovernanceBridge
from .memory_bridge import MemoryBridge

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
    "process_packet",
    "AgentController",
    "ReasoningEngine",
    "DecisionSynthesizer",
    "PacketRouter",
    "GovernanceBridge",
    "MemoryBridge",
    "__version__",
    "__footer_meta__",
    "__l9_trace__",
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
