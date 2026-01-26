"""
L9 Pattern Orchestrator - Interface Definitions
================================================

Pydantic models and type definitions for the pattern orchestrator.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Interface Definitions",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:01:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "interface",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "orchestrators.pattern.__init__",
            "orchestrators.pattern.orchestrator",
            "tests.orchestrators.test_pattern_orchestrator",
        ],
    },
}
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    """Types of pipeline nodes."""

    REASONING = "reasoning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    APPROVAL = "approval"


class NodeStatus(str, Enum):
    """Execution status of a node."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Overall pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


# =============================================================================
# Input/Output Contracts
# =============================================================================


class InputField(BaseModel):
    """Definition of a node input field."""

    name: str
    type: str = "object"
    required: bool = False
    description: str = ""


class OutputContract(BaseModel):
    """Definition of a node's output contract."""

    packet_type: str
    schema: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Node Definitions
# =============================================================================


class NodeDefinition(BaseModel):
    """Definition of a pipeline node from pattern YAML."""

    id: str
    uid: str = ""
    name: str
    kind: NodeKind = NodeKind.REASONING
    role: str = "ArchitectAgent"
    description: str = ""
    input_contract: list[InputField] = Field(default_factory=list)
    output_contract: OutputContract | None = None
    memory_segment: str = "segment.default"
    next: list[str] = Field(default_factory=list)


class NodeResult(BaseModel):
    """Result of executing a single node."""

    node_id: str
    status: NodeStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None


# =============================================================================
# Pattern Configuration
# =============================================================================


class ObservabilityConfig(BaseModel):
    """Observability configuration from pattern YAML."""

    emit_metrics: list[str] = Field(default_factory=list)
    tracing: dict[str, Any] = Field(default_factory=dict)


class LImprovementLoopConfig(BaseModel):
    """L improvement loop configuration."""

    yield_threshold_pct: float = 10.0
    max_iterations: int = 5
    improvement_dimensions: int = 10


class PatternConfig(BaseModel):
    """Pattern configuration loaded from YAML."""

    spec_kind: str = "l9_architecture_pattern"
    version: int = 1
    revision: str = ""
    name: str = ""
    description: str = ""
    nodes: list[NodeDefinition] = Field(default_factory=list)
    phase_0_mandatory: dict[str, Any] = Field(default_factory=dict)
    l_improvement_loop_config: LImprovementLoopConfig = Field(
        default_factory=LImprovementLoopConfig
    )
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)


# =============================================================================
# Subsystem Configuration
# =============================================================================


class SubsystemMetadata(BaseModel):
    """Metadata for a subsystem."""

    name: str
    domain: str = ""
    criticality: str = "medium"
    agents_involved: list[str] = Field(default_factory=list)


class ApprovalLevel(BaseModel):
    """Definition of an approval level."""

    name: str
    criteria: list[str] = Field(default_factory=list)
    approver: str = ""
    sla_minutes: int = 0


class ApprovalModel(BaseModel):
    """Approval model configuration."""

    levels: list[ApprovalLevel] = Field(default_factory=list)


class MemorySegment(BaseModel):
    """Memory segment configuration."""

    name: str
    writes: list[str] = Field(default_factory=list)


class MemoryModel(BaseModel):
    """Memory model configuration."""

    segments: list[MemorySegment] = Field(default_factory=list)


class RiskModel(BaseModel):
    """Risk assessment model."""

    assessment_dimensions: list[str] = Field(default_factory=list)
    high_risk_triggers: list[str] = Field(default_factory=list)


class PipelineStage(BaseModel):
    """Pipeline stage definition."""

    name: str
    description: str = ""


class PipelineConfig(BaseModel):
    """Pipeline configuration."""

    stages: list[PipelineStage] = Field(default_factory=list)


class SubsystemConfig(BaseModel):
    """Full subsystem configuration loaded from YAML."""

    subsystem_config_v1: dict[str, Any] | None = None

    # Flattened fields for direct access
    metadata: SubsystemMetadata = Field(
        default_factory=lambda: SubsystemMetadata(name="unknown")
    )
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    approval_model: ApprovalModel = Field(default_factory=ApprovalModel)
    memory_model: MemoryModel = Field(default_factory=MemoryModel)
    risk_model: RiskModel = Field(default_factory=RiskModel)

    def model_post_init(self, __context: Any) -> None:
        """Flatten nested config structure."""
        if self.subsystem_config_v1:
            cfg = self.subsystem_config_v1
            if "metadata" in cfg:
                self.metadata = SubsystemMetadata(**cfg["metadata"])
            if "goals" in cfg:
                self.goals = cfg["goals"]
            if "constraints" in cfg:
                self.constraints = cfg["constraints"]
            if "risks" in cfg:
                self.risks = cfg["risks"]


# =============================================================================
# Pipeline Results
# =============================================================================


class PipelineResult(BaseModel):
    """Result of a complete pipeline execution."""

    trace_id: UUID
    subsystem: str
    status: PipelineStatus
    node_results: list[NodeResult] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    failed_node: str | None = None
    error: str | None = None
    total_duration_ms: float = 0.0
    started_at: datetime
    completed_at: datetime | None = None

    @property
    def nodes_completed(self) -> int:
        """Count of successfully completed nodes."""
        return sum(1 for r in self.node_results if r.status == NodeStatus.SUCCESS)

    @property
    def is_success(self) -> bool:
        """Whether pipeline completed successfully."""
        return self.status == PipelineStatus.SUCCESS


# =============================================================================
# Request Models
# =============================================================================


class PipelineRequest(BaseModel):
    """Request to execute a pipeline."""

    user_prompts: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
    max_iterations: int | None = None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-024",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "config",
        "data-models",
        "enum",
        "intelligence",
        "metrics",
        "pydantic",
        "tracing",
        "validation",
    ],
    "keywords": [
        "approval",
        "completed",
        "contract",
        "definition",
        "definitions",
        "field",
        "improvement",
        "interface",
    ],
    "business_value": "Provides interface components including NodeKind, NodeStatus, PipelineStatus",
    "last_modified": "2026-01-17T23:47:56Z",
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
