"""
L9 Research Factory - Schema Parser
====================================

Parses YAML agent schemas into validated Pydantic models.

The Research Factory schema format (v6.0+) requires 12 sections:
1. system - Agent identity and role
2. integration - Dependencies and wiring points
3. governance - Escalation, compliance, audit scope
4. memorytopology - Working/episodic/semantic/causal/archive memory
5. communicationstack - Input/output/channels
6. reasoningengine - Logic framework and modes
7. collaborationnetwork - Partners and interaction protocol
8. learningsystem - Feedback loops and autonomy profile
9. worldmodelintegration - External context integration
10. cursorinstructions - File generation directives
11. deployment - Runtime, endpoints, telemetry
12. metadata - Version, owner, status

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Parser",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-06T16:58:23Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "schema_parser",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis", "S3"],
        "memory_layers": ["episodic_memory", "semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# =============================================================================
# Block 1: System Block
# =============================================================================


class SystemBlock(BaseModel):
    """
    Agent identity and role definition.

    Example:
        system: L9 Main Agent
        module: coreagent
        name: MainAgent
        role: Central Domain-Tensor Orchestrator...
        rootpath: L9/agents/main
    """

    system: str = Field(..., description="Full agent name/identity")
    module: str = Field(..., description="Functional area/module name")
    name: str = Field(..., description="PascalCase agent name")
    role: str = Field(..., description="Agent role description (2-3 sentences)")
    rootpath: str = Field(..., description="Base path for generated code")

    @field_validator("name")
    @classmethod
    def validate_name_pascal_case(cls, v: str) -> str:
        """Ensure name is PascalCase."""
        if not v[0].isupper():
            raise ValueError(f"Agent name must be PascalCase, got: {v}")
        return v


# =============================================================================
# Block 2: Integration Block
# =============================================================================


class IntegrationBlock(BaseModel):
    """
    Dependencies and wiring points.

    Example:
        integration:
          connectto:
            - L9/core
            - L9/worldmodel
          shareddomains:
            - PlastOS
            - MortgageOS
    """

    connectto: list[str] = Field(
        default_factory=list, description="Paths this agent connects to"
    )
    shareddomains: list[str] = Field(
        default_factory=list, description="Domains this agent serves"
    )


# =============================================================================
# Block 3: Governance Block
# =============================================================================


class GovernanceBlock(BaseModel):
    """
    Escalation, compliance, and audit configuration.

    Example:
        governance:
          anchors:
            - Igor
            - Compliance Officer
          mode: hybrid
          humanoverride: true
          escalationpolicy: Auto-escalate if confidence < 0.7
          auditscope:
            - packet_reception
            - reasoning_decisions
    """

    anchors: list[str] = Field(
        default_factory=list, description="Human oversight anchors"
    )
    mode: str = Field(
        default="hybrid", description="Governance mode: hybrid|autonomous|supervised"
    )
    humanoverride: bool = Field(default=True, description="Allow human override")
    complianceauditor: str | None = Field(
        None, description="Path to compliance auditor script"
    )
    escalationpolicy: str | None = Field(None, description="When to escalate decisions")
    performancereporting: str | None = Field(
        None, description="Path to performance dashboard"
    )
    auditscope: list[str] = Field(default_factory=list, description="What to audit")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate governance mode."""
        valid_modes = {"hybrid", "autonomous", "supervised"}
        if v.lower() not in valid_modes:
            raise ValueError(
                f"Invalid governance mode: {v}. Must be one of: {valid_modes}"
            )
        return v.lower()


# =============================================================================
# Block 4: Memory Topology Block
# =============================================================================


class MemoryLayerConfig(BaseModel):
    """Configuration for a single memory layer."""

    storagetype: str = Field(..., description="Storage backend type")
    purpose: str = Field(..., description="What this layer stores")
    keyspace: str | None = Field(None, description="Key pattern for Redis-like storage")
    retention: str | None = Field(None, description="Data retention policy")
    indexby: list[str] | None = Field(None, description="Index fields")
    structure: list[dict[str, Any]] | None = Field(
        None, description="Graph structure definition"
    )
    schema_definition: list[dict[str, Any]] | None = Field(
        None, alias="schema", description="Causal schema definition"
    )


class CrossAgentSharingConfig(BaseModel):
    """Cross-agent memory sharing configuration."""

    enabled: bool = Field(default=False)
    layer: str | None = Field(None, description="Sharing layer name")


class MemoryTopologyBlock(BaseModel):
    """
    Multi-layer memory architecture.

    Layers:
    - workingmemory: Fast cache (Redis)
    - episodicmemory: Decision logs (PostgreSQL)
    - semanticmemory: Entity graphs (Neo4j)
    - causalmemory: Reasoning traces (HypergraphDB)
    - longtermpersistence: Archive (S3)
    """

    workingmemory: MemoryLayerConfig | None = None
    episodicmemory: MemoryLayerConfig | None = None
    semanticmemory: MemoryLayerConfig | None = None
    causalmemory: MemoryLayerConfig | None = None
    longtermpersistence: MemoryLayerConfig | None = None
    crossagentsharing: CrossAgentSharingConfig | None = None


# =============================================================================
# Block 5: Communication Stack Block
# =============================================================================


class ChannelConfig(BaseModel):
    """Communication channel configuration."""

    slack: bool = Field(default=False)
    email: bool = Field(default=False)
    webhook: bool = Field(default=False)
    api: bool = Field(default=True)


class CommunicationStackBlock(BaseModel):
    """
    Input/output communication configuration.

    Example:
        communicationstack:
          input: [structuredapi, messagesqueue]
          output: [structuredapi, eventstream]
          channels:
            slack: true
            email: false
    """

    input: list[str] = Field(default_factory=list, description="Input methods")
    output: list[str] = Field(default_factory=list, description="Output methods")
    channels: ChannelConfig | None = None


# =============================================================================
# Block 6: Reasoning Engine Block
# =============================================================================


class KnowledgeFusionConfig(BaseModel):
    """Knowledge fusion layer configuration."""

    mode: str = Field(default="blend", description="Fusion mode")
    sourceblend: list[str] = Field(default_factory=list, description="Sources to blend")


class ReasoningFeedbackConfig(BaseModel):
    """Reasoning feedback loop configuration."""

    policy: str = Field(default="reinforcement_reflection")
    rewardfunction: str | None = Field(None, description="How to measure success")
    penaltyfunction: str | None = Field(None, description="How to measure failure")
    retrainintervalhours: int = Field(
        default=168, description="Hours between retraining"
    )


class ReasoningEngineBlock(BaseModel):
    """
    Logic framework and reasoning modes.

    Example:
        reasoningengine:
          framework: multimodal_reflective
          model: gpt4_orchestrator
          strategymodes:
            - causal_inference
            - pattern_matching
    """

    framework: str = Field(
        default="multimodal_reflective", description="Reasoning framework"
    )
    model: str = Field(default="gpt-4o", description="Primary LLM model")
    secondarymodels: list[str] = Field(
        default_factory=list, description="Supporting models"
    )
    strategymodes: list[str] = Field(
        default_factory=list, description="Available reasoning strategies"
    )
    temporalscope: str | None = Field(None, description="Temporal context window")
    knowledgefusionlayer: KnowledgeFusionConfig | None = None
    reasoningfeedbackloop: ReasoningFeedbackConfig | None = None


# =============================================================================
# Block 7: Collaboration Network Block
# =============================================================================


class CollaboratorConfig(BaseModel):
    """Configuration for a collaborating agent."""

    name: str
    role: str
    interaction: str = Field(default="bidirectional")


class CollaborationNetworkBlock(BaseModel):
    """
    Partner agents and interaction protocols.

    Example:
        collaborationnetwork:
          collaborators:
            - name: TensorAIOS
              role: Neural scoring
              interaction: api_call
    """

    collaborators: list[CollaboratorConfig] = Field(default_factory=list)
    protocol: str = Field(
        default="PacketEnvelope", description="Communication protocol"
    )


# =============================================================================
# Block 8: Learning System Block
# =============================================================================


class AutonomyProfileConfig(BaseModel):
    """Autonomy profile configuration."""

    mode: str = Field(default="controlled_autonomy")
    tasklimit: str | None = Field(None, description="Max parallel tasks")
    decisionlatencymaxms: int = Field(default=1000, description="Max decision latency")
    escalationtriggers: list[str] = Field(default_factory=list)


class LearningSystemBlock(BaseModel):
    """
    Feedback loops and autonomy profile.

    Example:
        learningsystem:
          architecture: continuous_metalearning
          modules:
            - drift_detector
            - pattern_extractor
          feedbackchannels:
            - governance_bus
            - user_feedback
    """

    architecture: str = Field(default="continuous_metalearning")
    modules: list[str] = Field(default_factory=list, description="Learning modules")
    feedbackchannels: list[str] = Field(
        default_factory=list, description="Feedback sources"
    )
    autonomyprofile: AutonomyProfileConfig | None = None


# =============================================================================
# Block 9: World Model Integration Block
# =============================================================================


class WorldModelIntegrationBlock(BaseModel):
    """
    External context integration.

    Example:
        worldmodelintegration:
          enabled: true
          sources:
            - market_data
            - entity_graph
          updatefrequency: realtime
    """

    enabled: bool = Field(default=True)
    sources: list[str] = Field(
        default_factory=list, description="World model data sources"
    )
    updatefrequency: str = Field(default="realtime", description="How often to update")
    contextwindow: str | None = Field(None, description="Context window size")


# =============================================================================
# Block 10: Cursor Instructions Block
# =============================================================================


class CursorInstructionsBlock(BaseModel):
    """
    File generation directives for code extraction.

    Example:
        cursorinstructions:
          createifmissing:
            - L9/agents/main
            - L9/agents/main/modules
          generatefiles:
            - controller.py
            - router.py
          linkexisting:
            - L9/core/governance.py
          generatedocs:
            - README.md
            - API_SPEC.md
    """

    createifmissing: list[str] = Field(
        default_factory=list, description="Directories to create"
    )
    generatefiles: list[str] = Field(
        default_factory=list, description="Files to generate"
    )
    linkexisting: list[str] = Field(
        default_factory=list, description="Existing files to link"
    )
    generatedocs: list[str] = Field(
        default_factory=list, description="Documentation to generate"
    )
    postgeneration: dict[str, Any] | None = Field(
        None, description="Post-generation actions"
    )


# =============================================================================
# Block 11: Deployment Block
# =============================================================================


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""

    metrics: bool = Field(default=True)
    tracing: bool = Field(default=True)
    logging: bool = Field(default=True)
    dashboardpath: str | None = Field(None)


class DeploymentBlock(BaseModel):
    """
    Runtime, endpoints, and telemetry configuration.

    Example:
        deployment:
          runtime: python_3.11_async
          endpoints:
            - /agent/main/status
            - /agent/main/process
          telemetry:
            metrics: true
            tracing: true
    """

    runtime: str = Field(default="python_3.11_async", description="Runtime environment")
    endpoints: list[str] = Field(
        default_factory=list, description="API endpoints to expose"
    )
    healthcheck: str | None = Field(None, description="Health check endpoint")
    telemetry: TelemetryConfig | None = None
    replicas: int = Field(default=1, description="Number of replicas")
    resources: dict[str, Any] | None = Field(None, description="Resource requirements")


# =============================================================================
# Block 12: Metadata Block
# =============================================================================


class MetadataBlock(BaseModel):
    """
    Version, owner, and status information.

    Example:
        metadata:
          version: 6.0.0
          created: 2025-01-01
          updated: 2025-01-15
          owner: L9 System Architect
          status: production
          tags:
            - core-agent
            - orchestration
    """

    version: str = Field(default="1.0.0", description="Schema version")
    created: str | None = Field(None, description="Creation date")
    updated: str | None = Field(None, description="Last update date")
    owner: str | None = Field(None, description="Schema owner")
    status: str = Field(default="draft", description="Status: draft|review|production")
    tags: list[str] = Field(default_factory=list, description="Classification tags")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        valid_statuses = {"draft", "review", "production", "deprecated"}
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of: {valid_statuses}")
        return v.lower()


# =============================================================================
# Main Agent Schema Model
# =============================================================================


class AgentSchema(BaseModel):
    """
    Complete agent schema model with all 12 required sections.

    This is the main model that represents a parsed Research Factory schema.
    """

    # Required identity fields (parsed from YAML frontmatter or system block)
    title: str | None = Field(None, description="Schema title")
    purpose: str | None = Field(None, description="Agent purpose")
    summary: str | None = Field(None, description="Agent summary")
    description: str | None = Field(None, description="Detailed description")

    # The 12 required blocks - ALL REQUIRED, NO DEFAULTS
    # v2.5: Missing sections = HARD FAIL
    system: SystemBlock = Field(..., description="Agent identity and role")
    integration: IntegrationBlock = Field(
        ..., description="Dependencies and wiring points"
    )
    governance: GovernanceBlock = Field(
        ..., description="Escalation, compliance, audit scope"
    )
    memorytopology: MemoryTopologyBlock = Field(
        ..., description="Memory layer configuration"
    )
    communicationstack: CommunicationStackBlock = Field(
        ..., description="Input/output/channels"
    )
    reasoningengine: ReasoningEngineBlock = Field(
        ..., description="Logic framework and modes"
    )
    collaborationnetwork: CollaborationNetworkBlock = Field(
        ..., description="Partners and protocol"
    )
    learningsystem: LearningSystemBlock = Field(
        ..., description="Feedback loops and autonomy"
    )
    worldmodelintegration: WorldModelIntegrationBlock = Field(
        ..., description="External context integration"
    )
    cursorinstructions: CursorInstructionsBlock = Field(
        ..., description="File generation directives"
    )
    deployment: DeploymentBlock = Field(
        ..., description="Runtime, endpoints, telemetry"
    )
    metadata: MetadataBlock = Field(..., description="Version, owner, status")

    # STRICT: Reject unknown fields
    model_config = {"extra": "forbid"}

    def get_agent_id(self) -> str:
        """Generate a unique agent ID from the schema."""
        name = self.system.name.lower().replace(" ", "-")
        version = self.metadata.version.replace(".", "-")
        return f"{name}-v{version}"

    def get_output_path(self) -> Path:
        """Get the output path for generated code."""
        return Path(self.system.rootpath)


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_schema(source: str | Path | dict[str, Any]) -> AgentSchema:
    """
    Parse a YAML schema into an AgentSchema model.

    Args:
        source: YAML string, file path, or pre-parsed dict

    Returns:
        Validated AgentSchema instance

    Raises:
        ValueError: If schema is invalid
        FileNotFoundError: If file path doesn't exist
    """
    # Handle different input types
    if isinstance(source, dict):
        data = source
    elif isinstance(source, Path):
        if not source.exists():
            raise FileNotFoundError(f"Schema file not found: {source}")
        with open(source) as f:
            content = f.read()
        data = yaml.safe_load(content)
    elif isinstance(source, str):
        # Check if it looks like a file path (short, no newlines, has extension)
        # Avoid calling Path.exists() on long YAML strings which causes OSError
        looks_like_path = (
            len(source) < 500
            and "\n" not in source
            and ("/" in source or "\\" in source or source.endswith((".yaml", ".yml")))
        )
        if looks_like_path:
            path = Path(source)
            if path.exists():
                with open(path) as f:
                    content = f.read()
                data = yaml.safe_load(content)
            else:
                # Not a valid file path, try parsing as YAML
                data = yaml.safe_load(source)
        else:
            # Parse as YAML string
            data = yaml.safe_load(source)
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    if data is None:
        raise ValueError("Empty schema")

    # Handle system block that might be a string (e.g., "system: L9 Main Agent")
    if "system" in data and isinstance(data["system"], str):
        # Convert string-style system to block format
        system_name = data["system"]
        data["system"] = {
            "system": system_name,
            "module": data.get("module", "agent"),
            "name": data.get("name", system_name.replace(" ", "")),
            "role": data.get("role", data.get("description", "")),
            "rootpath": data.get(
                "rootpath", f"L9/agents/{system_name.lower().replace(' ', '_')}"
            ),
        }

    # Parse and validate
    try:
        schema = AgentSchema.model_validate(data)
        logger.info(
            "Parsed schema: agent=%s, version=%s",
            schema.system.name,
            schema.metadata.version,
        )
        return schema
    except Exception as e:
        logger.error("Failed to parse schema: %s", str(e))
        raise ValueError(f"Invalid schema: {e}") from e


def parse_schema_file(filepath: str | Path) -> AgentSchema:
    """
    Parse a schema from a file path.

    Args:
        filepath: Path to YAML schema file

    Returns:
        Validated AgentSchema instance
    """
    return parse_schema(Path(filepath))


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main schema
    "AgentSchema",
    # Block models
    "SystemBlock",
    "IntegrationBlock",
    "GovernanceBlock",
    "MemoryTopologyBlock",
    "CommunicationStackBlock",
    "ReasoningEngineBlock",
    "CollaborationNetworkBlock",
    "LearningSystemBlock",
    "WorldModelIntegrationBlock",
    "CursorInstructionsBlock",
    "DeploymentBlock",
    "MetadataBlock",
    # Sub-models
    "MemoryLayerConfig",
    "ChannelConfig",
    "CollaboratorConfig",
    "TelemetryConfig",
    # Functions
    "parse_schema",
    "parse_schema_file",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-007",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "caching",
        "config",
        "data-models",
        "engine",
        "event-driven",
        "filesystem",
        "foundation",
        "linting",
    ],
    "keywords": [
        "agent",
        "audit",
        "autonomy",
        "block",
        "case",
        "channel",
        "collaboration",
        "collaborator",
    ],
    "business_value": "1. system - Agent identity and role 2. integration - Dependencies and wiring points 3. governance - Escalation, compliance, audit scope 4. memorytopology - Working/episodic/semantic/causal/archive mem",
    "last_modified": "2026-01-06T16:58:23Z",
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
