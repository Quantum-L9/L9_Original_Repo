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

from orchestrators.pattern.orchestrator import PatternOrchestrator
from orchestrators.pattern.interface import (
    PatternConfig,
    SubsystemConfig,
    NodeDefinition,
    PipelineResult,
    NodeResult,
)

__all__ = [
    "PatternOrchestrator",
    "PatternConfig",
    "SubsystemConfig",
    "NodeDefinition",
    "PipelineResult",
    "NodeResult",
]

__version__ = "1.0.0"
