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

from .phase_0_validate import validate_agent_blueprint
from .phase_1_load_kernels import load_and_parse_kernels, KernelParsed, KERNEL_ORDER
from .phase_2_instantiate import instantiate_agent, BootstrapInstanceData
from .phase_3_bind_kernels import bind_kernels_to_agent
from .phase_4_load_identity import load_identity_persona
from .phase_5_bind_tools import bind_tools_and_capabilities
from .phase_6_wire_governance import wire_governance_gates
from .phase_7_verify_and_lock import verify_and_lock
from .orchestrator import AgentBootstrapOrchestrator
from .bootstrap_metrics import (
    BootstrapMetrics,
    get_bootstrap_metrics,
    PROMETHEUS_AVAILABLE as BOOTSTRAP_PROMETHEUS_AVAILABLE,
)

__all__ = [
    "AgentBootstrapOrchestrator",
    "validate_agent_blueprint",
    "load_and_parse_kernels",
    "KernelParsed",
    "KERNEL_ORDER",
    "instantiate_agent",
    "BootstrapInstanceData",
    "bind_kernels_to_agent",
    "load_identity_persona",
    "bind_tools_and_capabilities",
    "wire_governance_gates",
    "verify_and_lock",
    # Metrics
    "BootstrapMetrics",
    "get_bootstrap_metrics",
    "BOOTSTRAP_PROMETHEUS_AVAILABLE",
]
