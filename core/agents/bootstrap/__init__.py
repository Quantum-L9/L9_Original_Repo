"""
L9 Agent Bootstrap Ceremony - Atomic 7-Phase Initialization

Harvested from: docs/__01-04-2026/__Agent Initialization - Paradigm Shift/L-Bootstrap/L9-Agent-Bootstrap-Architecture.md
Applied: L9 patterns (structlog, async, Pydantic)

This module implements frontier-lab grade agent initialization:
- All phases succeed atomically or roll back entirely
- Kernels, identity, tools, governance wired at startup
- Full audit trail with initialization signature
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Atomic 7-Phase Initialization",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "__init__",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .bootstrap_metrics import PROMETHEUS_AVAILABLE as BOOTSTRAP_PROMETHEUS_AVAILABLE
from .bootstrap_metrics import BootstrapMetrics, get_bootstrap_metrics
from .models import (
    AgentBootstrapContext,
    AgentBootstrapError,
    IdentityView,
    PhaseResult,
)
from .orchestrator import AgentBootstrapOrchestrator
from .phase_0_validate import validate_agent_blueprint
from .phase_1_load_kernels import KERNEL_ORDER, KernelParsed, load_and_parse_kernels
from .phase_2_instantiate import BootstrapInstanceData, instantiate_agent
from .phase_3_bind_kernels import bind_kernels_to_agent
from .phase_4_load_identity import load_identity_persona, load_identity_persona_view
from .phase_5_bind_tools import bind_tools_and_capabilities
from .phase_6_wire_governance import wire_governance_gates
from .phase_7_verify_and_lock import verify_and_lock, verify_and_lock_view

__all__ = [
    # Metrics
    "BOOTSTRAP_PROMETHEUS_AVAILABLE",
    "KERNEL_ORDER",
    # Models (dataclasses)
    "AgentBootstrapContext",
    "AgentBootstrapError",
    # Orchestrator
    "AgentBootstrapOrchestrator",
    # Phase data structures
    "BootstrapInstanceData",
    "BootstrapMetrics",
    "IdentityView",
    "KernelParsed",
    "PhaseResult",
    # Phase functions (legacy)
    "bind_kernels_to_agent",
    "bind_tools_and_capabilities",
    "get_bootstrap_metrics",
    "instantiate_agent",
    "load_and_parse_kernels",
    "load_identity_persona",
    # View functions (new)
    "load_identity_persona_view",
    "validate_agent_blueprint",
    "verify_and_lock",
    "verify_and_lock_view",
    "wire_governance_gates",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-232",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["agent-execution", "api", "audit-tool", "foundation", "metrics", "schema"],
    "keywords": [
        "agent",
        "atomic",
        "audit",
        "bootstrap",
        "governance",
        "initialization",
        "module",
        "phase",
    ],
    "business_value": "All phases succeed atomically or roll back entirely Kernels, identity, tools, governance wired at startup Full audit trail with initialization signature",
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
