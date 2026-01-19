"""
L9 Core Schemas - Capability Model
==================================

Agent capability sandboxing for L9 security layer.

Defines:
- ToolName: Enumeration of available tools
- Capability: Single tool permission
- AgentCapabilities: Per-agent capability set

Security Model:
- Each agent declares capabilities on handshake
- Orchestrator validates tool invocations against capabilities
- Capabilities are immutable once handshake is complete

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Capability Model",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-09T01:57:28Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "capabilities",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "ci.check_tool_wiring",
            "core.agents.kernel_registry",
            "core.governance.approval_gate",
            "core.schemas.__init__",
            "core.schemas.event_stream",
            "orchestration.task_router",
        ],
    },
}
# ============================================================================

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ToolName(str, Enum):
    """
    Enumeration of L9 tools that can be capability-gated.

    Categories:
    - Execution: shell, browser, python
    - Memory: memory_read, memory_write
    - Knowledge: world_model_query, kernel_read
    - System: os_control, file_access
    """

    # Execution tools
    SHELL = "shell"
    BROWSER = "browser"
    PYTHON = "python"

    # Memory tools
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    MEMORY_SEARCH = "memory_search"

    # Knowledge tools
    WORLD_MODEL_QUERY = "world_model_query"
    KERNEL_READ = "kernel_read"

    # System tools (added for completeness)
    OS_CONTROL = "os_control"
    FILE_ACCESS = "file_access"
    NETWORK = "network"

    # Governance and execution tools
    GMP_RUN = "gmp_run"
    GIT_COMMIT = "git_commit"
    MCP_CALL_TOOL = "mcp_call_tool"
    MAC_AGENT_EXEC_TASK = "mac_agent_exec_task"

    # Long plan orchestration tools
    LONG_PLAN_EXECUTE = "long_plan_execute"
    LONG_PLAN_SIMULATE = "long_plan_simulate"

    # Symbolic computation tools (Quantum AI Factory)
    SYMBOLIC_COMPUTE = "symbolic_compute"
    SYMBOLIC_CODEGEN = "symbolic_codegen"
    SYMBOLIC_OPTIMIZE = "symbolic_optimize"

    # Simulation tools (IR graph evaluation)
    SIMULATION = "simulation"


class Capability(BaseModel):
    """
    Single capability for a tool.

    Attributes:
        tool: The tool this capability governs
        allowed: Whether the tool is allowed (True) or denied (False)
        rate_limit: Optional rate limit (invocations per minute)
        scope: Optional scope restriction (e.g., "read_only", "local_only", "requires_igor_approval")
    """

    tool: ToolName = Field(..., description="Tool this capability governs")
    allowed: bool = Field(default=True, description="Whether tool is allowed")
    rate_limit: Optional[int] = Field(None, ge=0, description="Max invocations/minute")
    scope: Optional[str] = Field(
        None,
        description="Scope restriction (e.g., 'read_only', 'local_only', 'requires_igor_approval')",
    )

    def requires_igor_approval(self) -> bool:
        """
        Check if this capability requires Igor's explicit approval.

        Returns:
            True if scope is "requires_igor_approval"
        """
        return self.scope == "requires_igor_approval"

    model_config = {"frozen": True}


class AgentCapabilities(BaseModel):
    """
    Complete capability set for an agent.

    Attributes:
        agent_id: Unique agent identifier
        capabilities: List of tool capabilities
        default_allowed: Whether unlisted tools are allowed by default
        max_recursion_depth: Maximum task recursion depth

    Usage:
        caps = AgentCapabilities(
            agent_id="coder-agent-1",
            capabilities=[
                Capability(tool=ToolName.SHELL, allowed=True, rate_limit=10),
                Capability(tool=ToolName.MEMORY_WRITE, allowed=True),
                Capability(tool=ToolName.NETWORK, allowed=False),
            ],
            default_allowed=False,
        )
    """

    agent_id: str = Field(..., min_length=1, description="Unique agent identifier")
    capabilities: List[Capability] = Field(
        default_factory=list, description="List of tool capabilities"
    )
    default_allowed: bool = Field(
        default=False, description="Whether unlisted tools are allowed by default"
    )
    max_recursion_depth: int = Field(
        default=3, ge=1, le=10, description="Maximum task recursion depth"
    )

    def is_tool_allowed(self, tool: ToolName) -> bool:
        """
        Check if a specific tool is allowed for this agent.

        Args:
            tool: The tool to check

        Returns:
            True if allowed, False otherwise
        """
        for cap in self.capabilities:
            if cap.tool == tool:
                return cap.allowed
        return self.default_allowed

    def get_capability(self, tool: ToolName) -> Optional[Capability]:
        """
        Get the capability for a specific tool.

        Args:
            tool: The tool to look up

        Returns:
            Capability if found, None otherwise
        """
        for cap in self.capabilities:
            if cap.tool == tool:
                return cap
        return None

    def list_allowed_tools(self) -> List[ToolName]:
        """
        List all explicitly allowed tools.

        Returns:
            List of allowed ToolName values
        """
        return [cap.tool for cap in self.capabilities if cap.allowed]

    def list_denied_tools(self) -> List[ToolName]:
        """
        List all explicitly denied tools.

        Returns:
            List of denied ToolName values
        """
        return [cap.tool for cap in self.capabilities if not cap.allowed]


# =============================================================================
# Default Capability Profiles
# =============================================================================

DEFAULT_READER_CAPABILITIES = AgentCapabilities(
    agent_id="default_reader",
    capabilities=[
        Capability(tool=ToolName.MEMORY_READ, allowed=True),
        Capability(tool=ToolName.WORLD_MODEL_QUERY, allowed=True),
        Capability(tool=ToolName.KERNEL_READ, allowed=True),
    ],
    default_allowed=False,
)

DEFAULT_CODER_CAPABILITIES = AgentCapabilities(
    agent_id="default_coder",
    capabilities=[
        Capability(tool=ToolName.SHELL, allowed=True, rate_limit=30),
        Capability(tool=ToolName.PYTHON, allowed=True),
        Capability(tool=ToolName.FILE_ACCESS, allowed=True),
        Capability(tool=ToolName.MEMORY_READ, allowed=True),
        Capability(tool=ToolName.MEMORY_WRITE, allowed=True),
        Capability(tool=ToolName.WORLD_MODEL_QUERY, allowed=True),
        Capability(tool=ToolName.KERNEL_READ, allowed=True),
        Capability(tool=ToolName.NETWORK, allowed=False),
    ],
    default_allowed=False,
)

DEFAULT_ARCHITECT_CAPABILITIES = AgentCapabilities(
    agent_id="default_architect",
    capabilities=[
        Capability(tool=ToolName.MEMORY_READ, allowed=True),
        Capability(tool=ToolName.MEMORY_WRITE, allowed=True),
        Capability(tool=ToolName.WORLD_MODEL_QUERY, allowed=True),
        Capability(tool=ToolName.KERNEL_READ, allowed=True),
        Capability(tool=ToolName.BROWSER, allowed=True, rate_limit=10),
        Capability(tool=ToolName.SHELL, allowed=False),
        Capability(tool=ToolName.PYTHON, allowed=False),
    ],
    default_allowed=False,
)

DEFAULT_L_CAPABILITIES = AgentCapabilities(
    agent_id="L",
    capabilities=[
        # Memory and knowledge tools (fully allowed)
        Capability(tool=ToolName.MEMORY_READ, allowed=True),
        Capability(tool=ToolName.MEMORY_WRITE, allowed=True),
        Capability(tool=ToolName.MEMORY_SEARCH, allowed=True),
        Capability(tool=ToolName.WORLD_MODEL_QUERY, allowed=True),
        Capability(tool=ToolName.KERNEL_READ, allowed=True),
        # Integration tools (fully allowed)
        Capability(tool=ToolName.MCP_CALL_TOOL, allowed=True),
        # Mac agent execution (requires Igor approval - executes shell commands)
        Capability(
            tool=ToolName.MAC_AGENT_EXEC_TASK,
            allowed=True,
            scope="requires_igor_approval",
        ),
        # Long plan orchestration tools (fully allowed)
        Capability(tool=ToolName.LONG_PLAN_EXECUTE, allowed=True),
        Capability(tool=ToolName.LONG_PLAN_SIMULATE, allowed=True),
        # Symbolic computation tools (Quantum AI Factory)
        Capability(tool=ToolName.SYMBOLIC_COMPUTE, allowed=True),
        Capability(tool=ToolName.SYMBOLIC_CODEGEN, allowed=True),
        Capability(tool=ToolName.SYMBOLIC_OPTIMIZE, allowed=True),
        # Simulation tools (IR graph evaluation)
        Capability(tool=ToolName.SIMULATION, allowed=True),
        # Governance tools (allowed but require Igor approval)
        Capability(tool=ToolName.GMP_RUN, allowed=True, scope="requires_igor_approval"),
        Capability(
            tool=ToolName.GIT_COMMIT, allowed=True, scope="requires_igor_approval"
        ),
        # Network remains gated
        Capability(tool=ToolName.NETWORK, allowed=False),
    ],
    default_allowed=False,
)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ToolName",
    "Capability",
    "AgentCapabilities",
    "DEFAULT_READER_CAPABILITIES",
    "DEFAULT_CODER_CAPABILITIES",
    "DEFAULT_ARCHITECT_CAPABILITIES",
    "DEFAULT_L_CAPABILITIES",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-074",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "authorization",
        "data-models",
        "enum",
        "foundation",
        "profiling",
        "pydantic",
        "rest-api",
        "validation",
    ],
    "keywords": [
        "agent",
        "allowed",
        "approval",
        "capabilities",
        "capability",
        "denied",
        "handshake",
        "igor",
    ],
    "business_value": "Provides capabilities components including ToolName, Capability, AgentCapabilities",
    "last_modified": "2026-01-09T01:57:28Z",
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
