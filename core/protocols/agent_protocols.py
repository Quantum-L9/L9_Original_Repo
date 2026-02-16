"""
L9 Agent Protocols - Core Abstractions
=======================================

Frontier-grade protocol definitions for agent subsystem following Dependency Inversion Principle.

**Top Frontier AI Lab Quality** - Production-ready abstractions for agent operations.

Features:
- ✅ Protocol-based abstractions for agent lifecycle and operations
- ✅ Type-safe interfaces with comprehensive type hints
- ✅ Enables dependency injection and testing
- ✅ Supports tool execution, state management, and activation
- ✅ Hot-swappable implementations

Protocols:
- ActivatableAgent: Agent with kernel activation capability
- ToolExecutor: Tool execution interface
- StateManager: Agent state management
- AgentOrchestrator: Agent orchestration and coordination
- AgentRegistry: Agent discovery and registration

Version: 1.0.0
GMP: di-dip-phase1-abstractions
Author: Top Frontier AI Lab
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Protocols",
    "module_version": "1.0.0",
    "created_by": "L9 DI/DIP Upgrade",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "agent_protocols",
    "type": "protocol",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "agents.base_agent",
            "core.di.container",
            "orchestrators.orchestrator_registry",
            "tests.unit.test_agent_protocols",
        ],
    },
}
# ============================================================================

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class AgentState(str, Enum):
    """Agent state enumeration."""

    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    TERMINATED = "terminated"


@runtime_checkable
class ActivatableAgent(Protocol):
    """
    Protocol for agents that can be activated with kernels.

    This replaces hasattr() checks with formal protocol adherence.
    Agents implementing this protocol can be kernel-activated.

    Example implementations:
    - BaseAgent: Standard agent base class
    - CustomAgent: User-defined agent implementations
    - MockAgent: Test double for agent testing
    """

    def kernel_activate(
        self, manifest: Any, context: dict[str, Any] | None = None
    ) -> Any:
        """
        Activate agent with kernel manifest.

        Args:
            manifest: Kernel manifest to activate
            context: Optional activation context

        Returns:
            KernelActivationResult indicating success/failure
        """
        ...

    def kernel_deactivate(self) -> bool:
        """
        Deactivate kernel from agent.

        Returns:
            True if deactivation successful
        """
        ...

    def get_kernel_state(self) -> Any | None:
        """
        Get current kernel state.

        Returns:
            Current KernelState or None if not activated
        """
        ...

    @property
    def agent_id(self) -> str:
        """Get unique agent identifier."""
        ...


@runtime_checkable
class ToolExecutor(Protocol):
    """
    Protocol for tool execution interface.

    Implementations must provide tool discovery, validation,
    and execution capabilities.

    Example implementations:
    - StandardToolExecutor: Default tool execution
    - SandboxedToolExecutor: Isolated tool execution
    - TracedToolExecutor: Tool execution with observability
    """

    @must_stay_async("callers use await")
    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a tool with parameters.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            context: Optional execution context

        Returns:
            Tool execution result
        """
        ...

    def list_available_tools(self) -> list[str]:
        """
        List available tools.

        Returns:
            List of tool names
        """
        ...

    def get_tool_schema(self, tool_name: str) -> dict[str, Any]:
        """
        Get tool parameter schema.

        Args:
            tool_name: Tool name

        Returns:
            JSON schema for tool parameters
        """
        ...

    def validate_tool_parameters(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> bool:
        """
        Validate tool parameters against schema.

        Args:
            tool_name: Tool name
            parameters: Parameters to validate

        Returns:
            True if valid
        """
        ...


@runtime_checkable
class StateManager(Protocol):
    """
    Protocol for agent state management.

    Implementations must provide state persistence, retrieval,
    and transition management for agents.

    Example implementations:
    - InMemoryStateManager: State stored in memory
    - PersistentStateManager: State persisted to storage
    - DistributedStateManager: State shared across instances
    """

    @must_stay_async("callers use await")
    async def get_state(self, agent_id: str) -> AgentState | None:
        """
        Get current state of an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Current AgentState or None if not found
        """
        ...

    @must_stay_async("callers use await")
    async def set_state(self, agent_id: str, state: AgentState) -> None:
        """
        Set state of an agent.

        Args:
            agent_id: Unique agent identifier
            state: New agent state
        """
        ...

    @must_stay_async("callers use await")
    async def transition_state(
        self, agent_id: str, from_state: AgentState, to_state: AgentState
    ) -> bool:
        """
        Transition agent state with validation.

        Args:
            agent_id: Unique agent identifier
            from_state: Expected current state
            to_state: Target state

        Returns:
            True if transition successful
        """
        ...

    @must_stay_async("callers use await")
    async def get_state_history(
        self, agent_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get state transition history.

        Args:
            agent_id: Unique agent identifier
            limit: Maximum number of history entries

        Returns:
            List of state transitions
        """
        ...


@runtime_checkable
class AgentOrchestrator(Protocol):
    """
    Protocol for agent orchestration and coordination.

    Implementations must provide agent lifecycle management,
    task routing, and coordination capabilities.

    Example implementations:
    - StandardOrchestrator: Default orchestration
    - PriorityOrchestrator: Priority-based task routing
    - DistributedOrchestrator: Multi-node orchestration
    """

    @must_stay_async("callers use await")
    async def register_agent(
        self, agent: ActivatableAgent, metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Register an agent with orchestrator.

        Args:
            agent: Agent instance to register
            metadata: Optional agent metadata

        Returns:
            Registration ID
        """
        ...

    @must_stay_async("callers use await")
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistered
        """
        ...

    @must_stay_async("callers use await")
    async def route_task(
        self, task: dict[str, Any], constraints: dict[str, Any] | None = None
    ) -> str:
        """
        Route task to appropriate agent.

        Args:
            task: Task specification
            constraints: Optional routing constraints

        Returns:
            Agent ID that received the task
        """
        ...

    @must_stay_async("callers use await")
    async def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        """
        Get agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status information
        """
        ...

    def list_agents(self) -> list[str]:
        """
        List all registered agents.

        Returns:
            List of agent IDs
        """
        ...


@runtime_checkable
class AgentRegistry(Protocol):
    """
    Protocol for agent discovery and registration.

    Implementations must provide agent registration, discovery,
    and metadata management.

    Example implementations:
    - InMemoryAgentRegistry: Registry in memory
    - PersistentAgentRegistry: Registry with persistence
    - DistributedAgentRegistry: Multi-node registry
    """

    def register(
        self,
        agent_id: str,
        agent_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register an agent.

        Args:
            agent_id: Unique agent identifier
            agent_type: Agent type/class
            metadata: Optional metadata
        """
        ...

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistered
        """
        ...

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """
        Get agent information.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent information or None
        """
        ...

    def find_agents(
        self, agent_type: str | None = None, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Find agents by type or filters.

        Args:
            agent_type: Optional agent type filter
            filters: Optional additional filters

        Returns:
            List of matching agents
        """
        ...

    def list_all(self) -> list[str]:
        """
        List all registered agent IDs.

        Returns:
            List of agent IDs
        """
        ...


@runtime_checkable
class AgentContext(Protocol):
    """
    Protocol for agent execution context.

    Implementations must provide context management for
    agent execution including memory, tools, and state.

    Example implementations:
    - StandardAgentContext: Default context
    - IsolatedAgentContext: Sandboxed context
    - SharedAgentContext: Multi-agent shared context
    """

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        ...

    @property
    def session_id(self) -> str | None:
        """Get session ID."""
        ...

    def get_memory(self, key: str) -> Any | None:
        """
        Get value from context memory.

        Args:
            key: Memory key

        Returns:
            Value or None
        """
        ...

    def set_memory(self, key: str, value: Any) -> None:
        """
        Set value in context memory.

        Args:
            key: Memory key
            value: Value to store
        """
        ...

    def get_metadata(self) -> dict[str, Any]:
        """
        Get context metadata.

        Returns:
            Metadata dictionary
        """
        ...


__all__ = [
    "ActivatableAgent",
    "AgentContext",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentState",
    "StateManager",
    "ToolExecutor",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-124",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "auth",
        "data-models",
        "enum",
        "executor",
        "foundation",
        "mocking",
        "orchestration",
        "testing",
        "tracing",
    ],
    "keywords": [
        "abstractions",
        "activatable",
        "activate",
        "activation",
        "agent",
        "agents",
        "all",
        "available",
    ],
    "business_value": "Provides agent protocols components including AgentState, ActivatableAgent, ToolExecutor",
    "last_modified": "2026-01-24T13:02:52Z",
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
