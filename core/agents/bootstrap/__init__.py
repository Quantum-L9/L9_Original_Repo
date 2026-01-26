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
