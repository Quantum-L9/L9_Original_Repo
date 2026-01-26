"""
L9 Pattern Orchestrator - Universal Architecture Pipeline
=========================================================

Provides a universal orchestrator for executing N-node architecture pipelines
across any L9 subsystem (code mutation, tools, auth, memory retrieval, etc.).

Architecture:
- Config-driven: Pattern YAML + Subsystem config
- Schema-validated: All node outputs validated via JSON Schema
- Observable: OpenTelemetry traces + Prometheus metrics
- Memory-integrated: Artifacts written to PacketEnvelope

Usage:
    from orchestrators.pattern import PatternOrchestrator

    orchestrator = PatternOrchestrator(
        pattern_path="config/patterns/pipeline_v1.yaml",
        subsystem_config_path="config/subsystems/code_mutation.yaml",
    )
    result = await orchestrator.execute(user_prompts=["Build X feature"])

Version: 1.0.0
"""

from orchestrators.pattern.cell_adapter import (
    CellAgentAdapter,
    DirectLLMAgent,
    create_cell_adapter,
    create_direct_agent,
)
from orchestrators.pattern.interface import (
    NodeDefinition,
    NodeResult,
    PatternConfig,
    PipelineResult,
    SubsystemConfig,
)
from orchestrators.pattern.master_orchestrator import (
    MasterExecutionResult,
    MasterOrchestrator,
    create_master_orchestrator,
)
from orchestrators.pattern.orchestrator import PatternOrchestrator

__all__ = [
    # Agent adapters
    "CellAgentAdapter",
    "DirectLLMAgent",
    "MasterExecutionResult",
    # Multi-subsystem orchestration
    "MasterOrchestrator",
    "NodeDefinition",
    "NodeResult",
    "PatternConfig",
    # Single-subsystem orchestration
    "PatternOrchestrator",
    "PipelineResult",
    "SubsystemConfig",
    "create_cell_adapter",
    "create_direct_agent",
    "create_master_orchestrator",
]

__version__ = "1.0.0"
