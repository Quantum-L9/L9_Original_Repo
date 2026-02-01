"""
L9 Core Agents - Schemas
========================

Pydantic schemas for agent tasks, configurations, and execution state.

Defines:
- AgentTask: Work to be done by an agent
- AgentConfig: Configuration for an agent instance
- AIOSResult: Result from AIOS reasoning call
- ExecutorState: State machine states for executor loop
- ToolCallRequest: Request to dispatch a tool call
- ToolCallResult: Result from a tool call

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-001",
    "component_name": "Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-18T02:34:46Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "schemas",
    "type": "enum",
    "status": "active",
    "purpose": "Provides schemas components including ExecutorState, TaskKind, AgentTask",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "_archived.legacy_slack.webhook_slack",
            "api.agent_routes",
            "api.routes.commands",
            "api.server",
            "core.agents.__init__",
            "core.agents.agent_instance",
            "core.agents.bootstrap.orchestrator",
            "core.agents.bootstrap.phase_0_validate",
            "core.agents.bootstrap.phase_2_instantiate",
            "core.agents.executor",
        ],
    },
}
# ============================================================================

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from pydantic import BaseModel, Field

# =============================================================================
# Constants
# =============================================================================

AGENT_EXECUTOR_NAMESPACE = uuid5(NAMESPACE_DNS, "agent.executor.l9.internal")

# =============================================================================
# Enums
# =============================================================================


class ExecutorState(str, Enum):
    """State machine states for the executor loop."""

    INITIALIZING = "initializing"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class TaskKind(str, Enum):
    """Kind of agent task.

    DEPRECATED: Use AgentType instead for new code.
    Maintained for backward compatibility only.
    """

    QUERY = "query"
    COMMAND = "command"
    RESEARCH = "research"
    EXECUTION = "execution"
    CONVERSATION = "conversation"


class AgentType(str, Enum):
    """
    Enterprise agent classification for multi-agent routing.

    Each type maps to specific capabilities, security levels, and tool access.
    Used for:
    - Task routing decisions
    - Capability matching
    - Security policy enforcement
    - Billing/metering by agent type

    Replaces deprecated TaskKind enum.
    """

    # Core L9 agent types
    ASSISTANT = "assistant"  # Conversational, user-facing (replaces CONVERSATION)
    EXECUTOR = "executor"  # Code/tool execution (replaces EXECUTION)
    ANALYST = "analyst"  # Data analysis, queries (replaces QUERY)
    RESEARCHER = "researcher"  # Deep investigation (replaces RESEARCH)
    OPERATOR = "operator"  # System operations (replaces COMMAND)

    # Multi-agent ecosystem types (future)
    COORDINATOR = "coordinator"  # Orchestrates other agents
    SPECIALIST = "specialist"  # Domain-specific expert
    SUPERVISOR = "supervisor"  # Reviews/approves other agents' work

    # External agent types
    EXTERNAL = "external"  # Third-party agent integration
    WORKER = "worker"  # Mac agent, remote executors


# =============================================================================
# Agent Task
# =============================================================================


class AgentTask(BaseModel):
    """
    Defines the work to be done by an agent.

    Contains the target agent, context, payload, and execution parameters.

    Attributes:
        id: Unique task identifier
        kind: Type of task for routing
        agent_id: Target agent identifier (e.g., "l9-standard-v1")
        source_id: Source that created this task
        thread_identifier: Logical thread for conversation grouping
        payload: Task-specific data
        context: Additional context for execution
        created_at: Task creation timestamp
        timeout_ms: Execution timeout in milliseconds
        max_iterations: Maximum reasoning iterations allowed
    """

    id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    kind: TaskKind = Field(default=TaskKind.QUERY, description="Task kind for routing")
    agent_id: str = Field(..., description="Target agent identifier")
    source_id: str = Field(
        default="system", description="Source that created this task"
    )
    thread_identifier: str | None = Field(
        None, description="Thread identifier for grouping"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Task-specific data"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional execution context"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    timeout_ms: int = Field(
        default=120000, ge=1000, description="Execution timeout (ms)"
    )
    max_iterations: int = Field(
        default=10, ge=1, le=100, description="Max reasoning iterations"
    )

    # === FUTURE-PROOF FIELDS (enterprise multi-agent architecture) ===
    agent_type: AgentType = Field(
        default=AgentType.ASSISTANT,
        description="FUTURE-PROOF: Enterprise agent classification for routing and policy enforcement",
    )
    target_domain: str = Field(
        default="l9",
        pattern=r"^(l9|l10|external|sandbox)$",
        description="FUTURE-PROOF: Target domainOS - validated against known domains",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="FUTURE-PROOF: Task urgency (1=critical/blocking, 5=normal, 10=background/batch)",
    )
    delegation_chain: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="FUTURE-PROOF: Agent IDs that have handled this task (audit trail, max 50 hops)",
    )
    capability_requirements: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="FUTURE-PROOF: Required capabilities ('shell_access', 'neo4j', 'memory_write', 'external_api')",
    )

    model_config = {"extra": "forbid"}

    def get_thread_id(self) -> UUID:
        """
        Generate deterministic thread UUID from stable thread identity.

        Uses UUIDv5 with namespace and source_id + thread_identifier.
        Thread UUID is NOT derived from task ID to ensure thread stability.
        """
        identity = f"{self.source_id}:{self.thread_identifier or 'default'}"
        return uuid5(AGENT_EXECUTOR_NAMESPACE, identity)

    def get_dedupe_key(self) -> str:
        """Get deduplication key for idempotency checking."""
        return str(self.id)


# =============================================================================
# Agent Config
# =============================================================================


class ToolBinding(BaseModel):
    """
    A tool bound to an agent instance.

    Identity: tool_id is the SOLE canonical identity.
    display_name is for UI/logs only - never used for lookup, dispatch, or binding.
    """

    tool_id: str = Field(
        ..., description="Canonical tool identity (used for all lookups/dispatch)"
    )
    display_name: str | None = Field(
        None, description="Human-readable name for UI/logs only"
    )
    description: str | None = Field(None, description="Tool description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for tool input parameters"
    )
    enabled: bool = Field(
        default=True, description="Whether tool is enabled for this binding"
    )


class AgentConfig(BaseModel):
    """
    Configuration for an agent instance.

    Includes the agent's identity, personality reference, and bound toolset.

    Attributes:
        agent_id: Unique agent identifier
        name: Human-readable agent name
        personality_id: Reference to agent personality/prompt definition
        model: LLM model to use
        temperature: LLM temperature
        max_tokens: Max response tokens
        tools: List of tools bound to this agent
        system_prompt: Optional system prompt override
        kernel_refs: List of kernel YAML files for bootstrap ceremony
        metadata: Additional configuration metadata
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(default="", description="Human-readable agent name")
    personality_id: str = Field(
        default="l9-standard-v1", description="Personality reference"
    )
    model: str = Field(default="gpt-4o", description="LLM model")
    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="LLM temperature"
    )
    max_tokens: int = Field(
        default=4000, ge=100, le=128000, description="Max response tokens"
    )
    tools: list[ToolBinding] = Field(default_factory=list, description="Bound tools")
    system_prompt: str | None = Field(None, description="System prompt override")
    kernel_refs: list[str] = Field(
        default_factory=list, description="Kernel YAML files for bootstrap ceremony"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Tool Call Types
# =============================================================================


class ToolCallRequest(BaseModel):
    """
    Request to dispatch a tool call.

    Generated by AIOS when reasoning produces a tool invocation.
    Identity: tool_id is the canonical tool identity - matches function.name in OpenAI schema.
    """

    call_id: UUID = Field(default_factory=uuid4, description="Unique call identifier")
    tool_id: str = Field(
        ..., description="Canonical tool identity (must match function.name)"
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments for tool"
    )
    task_id: UUID = Field(..., description="Parent task ID")
    iteration: int = Field(..., ge=0, description="Iteration number in execution loop")

    model_config = {"extra": "forbid"}


class ToolCallResult(BaseModel):
    """
    Result from a tool call.

    Returned by tool registry after dispatching.
    Identity: tool_id is tagged on result for context re-entry.
    """

    call_id: UUID = Field(..., description="Call identifier from request")
    tool_id: str = Field(
        ..., description="Canonical tool identity (for context re-entry)"
    )
    success: bool = Field(..., description="Whether call succeeded")
    result: Any = Field(None, description="Tool result if successful")
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: int = Field(default=0, ge=0, description="Execution duration")

    model_config = {"extra": "forbid"}


# =============================================================================
# AIOS Result
# =============================================================================


class AIOSResultType(str, Enum):
    """Type of AIOS result."""

    RESPONSE = "response"
    TOOL_CALL = "tool_call"
    ERROR = "error"


class AIOSResult(BaseModel):
    """
    Result from AIOS reasoning call.

    Contains either a final response or a tool call request.

    Attributes:
        result_type: Type of result (response, tool_call, error)
        content: Response content if result_type is RESPONSE
        tool_call: Tool call request if result_type is TOOL_CALL
        error: Error message if result_type is ERROR
        tokens_used: Total tokens used in this call
        finish_reason: LLM finish reason
    """

    result_type: AIOSResultType = Field(..., description="Type of result")
    content: str | None = Field(None, description="Response content")
    tool_call: ToolCallRequest | None = Field(
        None, description="Tool call if requested"
    )
    error: str | None = Field(None, description="Error message")
    tokens_used: int = Field(default=0, ge=0, description="Tokens used")
    finish_reason: str | None = Field(None, description="LLM finish reason")

    model_config = {"extra": "forbid"}

    @classmethod
    def response(cls, content: str, tokens_used: int = 0) -> AIOSResult:
        """Create a response result."""
        return cls(
            result_type=AIOSResultType.RESPONSE,
            content=content,
            tokens_used=tokens_used,
            finish_reason="stop",
        )

    @classmethod
    def tool_request(
        cls, tool_call: ToolCallRequest, tokens_used: int = 0
    ) -> AIOSResult:
        """Create a tool call result."""
        return cls(
            result_type=AIOSResultType.TOOL_CALL,
            tool_call=tool_call,
            tokens_used=tokens_used,
            finish_reason="tool_calls",
        )

    @classmethod
    def error_result(cls, error: str) -> AIOSResult:
        """Create an error result."""
        return cls(
            result_type=AIOSResultType.ERROR,
            error=error,
        )


# =============================================================================
# Execution Result
# =============================================================================


class ExecutionResult(BaseModel):
    """
    Final result of agent task execution.

    Attributes:
        task_id: Task that was executed
        status: Final execution status
        result: Final response content
        iterations: Total iterations performed
        duration_ms: Total execution duration
        error: Error message if failed
        trace_id: Trace ID for debugging
        tool_calls: List of tool calls made during execution
        tokens_used: Total tokens consumed across all LLM calls
    """

    task_id: UUID = Field(..., description="Task ID")
    status: str = Field(..., description="Final status: completed, failed, terminated")
    result: str | None = Field(None, description="Final response content")
    iterations: int = Field(default=0, ge=0, description="Total iterations")
    duration_ms: int = Field(default=0, ge=0, description="Total duration")
    error: str | None = Field(None, description="Error message if failed")
    trace_id: UUID | None = Field(None, description="Trace ID")
    tool_calls: list[ToolCallResult] | None = Field(
        None, description="List of tool calls made during execution"
    )
    tokens_used: int | None = Field(
        None, ge=0, description="Total tokens consumed across all LLM calls"
    )
    governance_blocks: list[dict[str, Any]] | None = Field(
        None,
        description="Governance blocks that occurred during execution (authority, safety, tool approval)",
    )
    user_corrections: list[dict[str, Any]] | None = Field(
        None,
        description="User corrections provided during execution for behavioral gap analysis",
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Idempotency Response
# =============================================================================


class DuplicateTaskResponse(BaseModel):
    """
    Response when a duplicate task is detected.

    IDEMPOTENCY LIMITATION: Currently in-memory only.
    Duplicate detection is lost on executor restart.
    Substrate-backed idempotency planned for v1.2.
    """

    ok: bool = Field(default=True)
    status: str = Field(default="duplicate")
    task_id: UUID = Field(..., description="Original task ID")

    model_config = {"extra": "forbid"}


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Constants
    "AGENT_EXECUTOR_NAMESPACE",
    "AIOSResult",
    "AIOSResultType",
    "AgentConfig",
    # Models
    "AgentTask",
    "AgentType",
    "DuplicateTaskResponse",
    "ExecutionResult",
    # Enums
    "ExecutorState",
    "TaskKind",
    "ToolBinding",
    "ToolCallRequest",
    "ToolCallResult",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# Extended metadata referenced by header

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "COR-FOUN-001",
    # === GOVERNANCE ===
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": [],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 500,
        "throughput_ops_per_sec": 100,
        "availability_percent": 99.9,
        "error_rate_percent": 0.1,
    },
    # === DISCOVERY ===
    "tags": ["data-models", "enum", "foundation", "llm", "pydantic", "validation"],
    "keywords": ["agent", "binding", "call", "config", "dedupe", "duplicate"],
    "business_value": "Provides schemas components including ExecutorState, TaskKind, AgentTask",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-18T02:34:46Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
