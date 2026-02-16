"""
L9 Kernel Schemas - Pydantic Models for Kernel Manifests
=========================================================

Defines the schema for all kernel types in the L9 system.
These models enforce structure validation at load time.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1

Kernel Types:
- MasterKernel: System law, sovereignty, modes
- IdentityKernel: Agent identity, personality, traits
- CognitiveKernel: Reasoning patterns, cognitive modes
- BehavioralKernel: Thresholds, prohibitions, defaults
- MemoryKernel: Memory architecture, retention policies
- WorldModelKernel: World model, entity relationships
- ExecutionKernel: State machine, task sizing
- SafetyKernel: Guardrails, prohibited actions
- DeveloperKernel: Developer discipline, coding rules
- PacketProtocolKernel: Load sequence, packet format
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Pydantic Models for Kernel Manifests",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "schemas",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.agents.kernel_registry",
            "core.kernels.kernelloader",
            "tests.unit.test_kernel_loader_activation",
        ],
    },
}
# ============================================================================

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Base Config - Allow extra fields for flexibility
# =============================================================================


class FlexibleModel(BaseModel):
    """Base model that allows extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow")


# =============================================================================
# Enums
# =============================================================================


class KernelType(str, Enum):
    """Kernel type identifiers."""

    MASTER = "master"
    IDENTITY = "identity"
    COGNITIVE = "cognitive"
    BEHAVIORAL = "behavioral"
    MEMORY = "memory"
    WORLDMODEL = "worldmodel"
    EXECUTION = "execution"
    SAFETY = "safety"
    DEVELOPER = "developer"
    PACKET_PROTOCOL = "packet_protocol"


class KernelState(str, Enum):
    """Kernel activation states."""

    INACTIVE = "INACTIVE"
    LOADING = "LOADING"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class RuleType(str, Enum):
    """Types of kernel rules."""

    CAPABILITY = "capability"
    SAFETY = "safety"
    BEHAVIORAL = "behavioral"
    IDENTITY = "identity"
    EXECUTION = "execution"
    MEMORY = "memory"


# =============================================================================
# Base Models
# =============================================================================


class KernelRule(FlexibleModel):
    """A single rule within a kernel."""

    id: str = Field(..., description="Unique rule identifier")
    type: str = Field(..., description="Rule type (capability, safety, etc.)")
    enabled: bool = Field(default=True, description="Whether rule is active")
    description: str | None = Field(default=None, description="Rule description")
    severity: str | None = Field(default="MEDIUM", description="Violation severity")
    enforcement: str | None = Field(default="strict", description="Enforcement mode")


class KernelInfo(FlexibleModel):
    """Core kernel metadata."""

    name: str = Field(..., description="Kernel name")
    version: str = Field(..., description="Kernel version (semver)")
    priority: int = Field(default=100, description="Load priority (lower = earlier)")
    description: str | None = Field(default=None, description="Kernel description")
    rules: list[KernelRule] = Field(default_factory=list, description="Kernel rules")


class KernelMeta(FlexibleModel):
    """Metadata attached during loading."""

    source_file: str | None = Field(default=None, description="Source file path")
    layer: str | None = Field(default=None, description="Layer name (00_system, etc.)")
    layer_order: int = Field(default=50, description="Layer load order")
    loaded_at: datetime | None = Field(default=None, description="Load timestamp")
    sha256: str | None = Field(default=None, description="File hash for integrity")


# =============================================================================
# Kernel-Specific Models
# =============================================================================


class SovereigntyConfig(FlexibleModel):
    """Master kernel sovereignty configuration."""

    owner: str = Field(default="Igor", description="System owner")
    allegiance: str = Field(default="Igor-only", description="Allegiance constraint")
    authority_hierarchy: list[str] = Field(
        default_factory=lambda: ["Igor", "L", "Research agents", "Mac agent"],
        description="Authority hierarchy (highest first)",
    )


class ModeConfig(FlexibleModel):
    """Operational mode configuration."""

    name: str = Field(..., description="Mode name")
    description: str | None = Field(default=None, description="Mode description")
    active: bool = Field(default=False, description="Whether mode is active")


class MasterKernelData(FlexibleModel):
    """Master kernel specific data."""

    sovereignty: SovereigntyConfig | None = None
    modes: dict[str, ModeConfig] = Field(default_factory=dict)
    system_law: str | None = Field(default=None, description="Core system law text")


class IdentityConfig(FlexibleModel):
    """Identity kernel configuration."""

    designation: str = Field(default="L", description="Agent designation")
    primary_role: str = Field(default="CTO for Igor", description="Primary role")
    allegiance: str = Field(default="Igor-only", description="Allegiance")
    mission: str | None = Field(default=None, description="Mission statement")
    traits: list[str] = Field(default_factory=list, description="Personality traits")
    anti_traits: list[str] = Field(
        default_factory=list, description="Traits to NEVER exhibit"
    )


class StyleConfig(FlexibleModel):
    """Communication style configuration."""

    tone: str = Field(default="direct", description="Communication tone")
    verbosity: str = Field(default="concise", description="Verbosity level")
    formality: str = Field(default="professional", description="Formality level")


class IdentityKernelData(FlexibleModel):
    """Identity kernel specific data."""

    identity: IdentityConfig | None = None
    personality: dict[str, Any] = Field(default_factory=dict)
    style: StyleConfig | None = None


class ThresholdsConfig(FlexibleModel):
    """Behavioral thresholds configuration."""

    execute: float = Field(default=0.8, ge=0.0, le=1.0, description="Execute threshold")
    questions_max: int = Field(
        default=1, ge=0, description="Max questions before acting"
    )
    hedges_max: int = Field(default=0, ge=0, description="Max hedges allowed")
    confidence_floor: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence to proceed"
    )


class Prohibition(FlexibleModel):
    """A behavioral prohibition."""

    name: str = Field(..., description="Prohibition name")
    detect: list[str] = Field(default_factory=list, description="Detection patterns")
    severity: str = Field(default="HIGH", description="Violation severity")
    action: str = Field(default="block", description="Action on violation")


class BehavioralKernelData(FlexibleModel):
    """Behavioral kernel specific data."""

    thresholds: ThresholdsConfig | None = None
    defaults: dict[str, Any] = Field(default_factory=dict)
    prohibitions: list[Prohibition] = Field(default_factory=list)


class GuardrailConfig(FlexibleModel):
    """Safety guardrail configuration."""

    name: str = Field(..., description="Guardrail name")
    enabled: bool = Field(default=True, description="Whether guardrail is active")
    description: str | None = Field(default=None, description="Guardrail description")
    enforcement: str = Field(default="strict", description="Enforcement mode")


class SafetyKernelData(FlexibleModel):
    """Safety kernel specific data."""

    guardrails: dict[str, GuardrailConfig] = Field(default_factory=dict)
    prohibited_actions: list[str] = Field(default_factory=list)
    confirmation_required: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)


class StateMachineConfig(FlexibleModel):
    """Execution state machine configuration."""

    initial_state: str = Field(default="IDLE", description="Initial state")
    states: list[str] = Field(default_factory=list, description="Valid states")
    transitions: dict[str, list[str]] = Field(
        default_factory=dict, description="State transitions"
    )


class TaskSizingConfig(FlexibleModel):
    """Task sizing configuration."""

    small: dict[str, Any] = Field(default_factory=dict)
    medium: dict[str, Any] = Field(default_factory=dict)
    large: dict[str, Any] = Field(default_factory=dict)


class ExecutionKernelData(FlexibleModel):
    """Execution kernel specific data."""

    state_machine: StateMachineConfig | None = None
    task_sizing: TaskSizingConfig | None = None
    timeout_defaults: dict[str, int] = Field(default_factory=dict)


class MemoryKernelData(FlexibleModel):
    """Memory kernel specific data."""

    retention_policy: dict[str, Any] = Field(default_factory=dict)
    indexing_rules: dict[str, Any] = Field(default_factory=dict)
    retrieval_config: dict[str, Any] = Field(default_factory=dict)


class WorldModelKernelData(FlexibleModel):
    """World model kernel specific data."""

    entity_types: list[str] = Field(default_factory=list)
    relationship_types: list[str] = Field(default_factory=list)
    inference_rules: dict[str, Any] = Field(default_factory=dict)


class CognitiveKernelData(FlexibleModel):
    """Cognitive kernel specific data."""

    reasoning_modes: dict[str, Any] = Field(default_factory=dict)
    cognitive_patterns: dict[str, Any] = Field(default_factory=dict)
    attention_config: dict[str, Any] = Field(default_factory=dict)


class DeveloperKernelData(FlexibleModel):
    """Developer kernel specific data."""

    coding_rules: dict[str, Any] = Field(default_factory=dict)
    review_checklist: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)


class LoadSequenceEntry(FlexibleModel):
    """Entry in the packet protocol load sequence."""

    file: str = Field(..., description="Kernel filename")
    required: bool = Field(default=True, description="Whether kernel is required")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")


class PacketProtocolKernelData(FlexibleModel):
    """Packet protocol kernel specific data."""

    load_sequence: dict[int, LoadSequenceEntry] = Field(default_factory=dict)
    packet_format: dict[str, Any] = Field(default_factory=dict)
    validation_rules: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Unified Kernel Manifest
# =============================================================================


class KernelManifest(FlexibleModel):
    """
    Unified kernel manifest model.

    Represents any kernel type with type-specific data.
    Used for validation during kernel loading.
    """

    kernel: KernelInfo = Field(..., description="Core kernel metadata")
    load_meta: KernelMeta | None = Field(default=None, description="Load metadata")

    # Type-specific data (only one populated per kernel)
    sovereignty: SovereigntyConfig | None = None
    modes: dict[str, ModeConfig] | None = None
    system_law: str | None = None

    identity: IdentityConfig | None = None
    personality: dict[str, Any] | None = None
    style: StyleConfig | None = None

    thresholds: ThresholdsConfig | None = None
    defaults: dict[str, Any] | None = None
    prohibitions: list[Prohibition] | None = None

    guardrails: dict[str, GuardrailConfig] | None = None
    prohibited_actions: list[str] | None = None
    confirmation_required: list[str] | None = None

    state_machine: StateMachineConfig | None = None
    task_sizing: TaskSizingConfig | None = None

    reasoning: dict[str, Any] | None = None
    cognitive: dict[str, Any] | None = None

    memory: dict[str, Any] | None = None
    worldmodel: dict[str, Any] | None = None
    developer: dict[str, Any] | None = None

    load_sequence: dict[str, Any] | None = None

    # Allow extra fields for forward compatibility
    model_config = {"extra": "allow"}

    @field_validator("kernel", mode="before")
    @classmethod
    def ensure_kernel_info(cls, v: Any) -> Any:
        """Ensure kernel info is properly structured."""
        if isinstance(v, dict):
            # Ensure required fields
            if "name" not in v:
                raise ValueError("kernel.name is required")
            if "version" not in v:
                v["version"] = "1.0.0"  # Default version
        return v

    def get_kernel_type(self) -> KernelType | None:
        """Infer kernel type from name."""
        name = self.kernel.name.lower()

        type_map = {
            "master": KernelType.MASTER,
            "identity": KernelType.IDENTITY,
            "cognitive": KernelType.COGNITIVE,
            "behavioral": KernelType.BEHAVIORAL,
            "memory": KernelType.MEMORY,
            "worldmodel": KernelType.WORLDMODEL,
            "world_model": KernelType.WORLDMODEL,
            "execution": KernelType.EXECUTION,
            "safety": KernelType.SAFETY,
            "developer": KernelType.DEVELOPER,
            "packet_protocol": KernelType.PACKET_PROTOCOL,
            "packet": KernelType.PACKET_PROTOCOL,
        }

        for key, kernel_type in type_map.items():
            if key in name:
                return kernel_type

        return None


# =============================================================================
# Validation Result
# =============================================================================


class ValidationError(FlexibleModel):
    """A single validation error."""

    field: str = Field(..., description="Field path that failed validation")
    message: str = Field(..., description="Error message")
    severity: str = Field(default="ERROR", description="Error severity")


class KernelValidationResult(FlexibleModel):
    """Result of kernel validation."""

    valid: bool = Field(..., description="Whether kernel is valid")
    kernel_name: str | None = Field(default=None, description="Kernel name")
    kernel_type: KernelType | None = Field(default=None, description="Inferred type")
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)


# =============================================================================
# Activation Result
# =============================================================================


class KernelActivationResult(FlexibleModel):
    """Result of two-phase kernel activation."""

    phase: str = Field(..., description="Current phase (LOAD or ACTIVATE)")
    success: bool = Field(..., description="Whether phase succeeded")
    kernels_loaded: int = Field(default=0, description="Number of kernels loaded")
    kernels_activated: int = Field(default=0, description="Number of kernels activated")
    integrity_verified: bool = Field(
        default=False, description="Integrity check passed"
    )
    validation_errors: list[ValidationError] = Field(default_factory=list)
    activation_context_set: bool = Field(
        default=False, description="Whether activation context was injected"
    )
    state: KernelState = Field(
        default=KernelState.INACTIVE, description="Final kernel state"
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "BehavioralKernelData",
    "CognitiveKernelData",
    "DeveloperKernelData",
    "ExecutionKernelData",
    "GuardrailConfig",
    "IdentityConfig",
    "IdentityKernelData",
    # Activation
    "KernelActivationResult",
    "KernelInfo",
    # Unified manifest
    "KernelManifest",
    "KernelMeta",
    # Base models
    "KernelRule",
    "KernelState",
    # Enums
    "KernelType",
    "KernelValidationResult",
    "LoadSequenceEntry",
    "MasterKernelData",
    "MemoryKernelData",
    "ModeConfig",
    "PacketProtocolKernelData",
    "Prohibition",
    "RuleType",
    "SafetyKernelData",
    # Kernel-specific models
    "SovereigntyConfig",
    "StateMachineConfig",
    "StyleConfig",
    "TaskSizingConfig",
    "ThresholdsConfig",
    # Validation
    "ValidationError",
    "WorldModelKernelData",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-004",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "data-models",
        "foundation",
        "messaging",
        "pydantic",
        "schema",
        "security",
        "validation",
    ],
    "keywords": [
        "activation",
        "agent",
        "behavioral",
        "cognitive",
        "developer",
        "ensure",
        "entry",
        "execution",
    ],
    "business_value": "Provides schemas components including FlexibleModel, KernelType, KernelState",
    "last_modified": "2026-01-14T15:03:00Z",
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
