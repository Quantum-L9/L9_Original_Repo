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

from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable
from enum import Enum


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
        self, manifest: Any, context: Optional[Dict[str, Any]] = None
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

    def get_kernel_state(self) -> Optional[Any]:
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

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

    def list_available_tools(self) -> List[str]:
        """
        List available tools.

        Returns:
            List of tool names
        """
        ...

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get tool parameter schema.

        Args:
            tool_name: Tool name

        Returns:
            JSON schema for tool parameters
        """
        ...

    def validate_tool_parameters(
        self, tool_name: str, parameters: Dict[str, Any]
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

    async def get_state(self, agent_id: str) -> Optional[AgentState]:
        """
        Get current state of an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Current AgentState or None if not found
        """
        ...

    async def set_state(self, agent_id: str, state: AgentState) -> None:
        """
        Set state of an agent.

        Args:
            agent_id: Unique agent identifier
            state: New agent state
        """
        ...

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

    async def get_state_history(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
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

    async def register_agent(
        self, agent: ActivatableAgent, metadata: Optional[Dict[str, Any]] = None
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

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistered
        """
        ...

    async def route_task(
        self, task: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None
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

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent status.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status information
        """
        ...

    def list_agents(self) -> List[str]:
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
        metadata: Optional[Dict[str, Any]] = None,
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

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent information.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent information or None
        """
        ...

    def find_agents(
        self, agent_type: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find agents by type or filters.

        Args:
            agent_type: Optional agent type filter
            filters: Optional additional filters

        Returns:
            List of matching agents
        """
        ...

    def list_all(self) -> List[str]:
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
    def session_id(self) -> Optional[str]:
        """Get session ID."""
        ...

    def get_memory(self, key: str) -> Optional[Any]:
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

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get context metadata.

        Returns:
            Metadata dictionary
        """
        ...


# Type aliases
# NOTE: Using Union[] instead of | for Python 3.9 compatibility (VPS runtime)
# See .cursor/rules/92-learned-lessons.mdc for why this matters
AgentProtocols = Union[
    ActivatableAgent,
    ToolExecutor,
    StateManager,
    AgentOrchestrator,
    AgentRegistry,
    AgentContext,
]


__all__ = [
    "ActivatableAgent",
    "ToolExecutor",
    "StateManager",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentContext",
    "AgentState",
    "AgentProtocols",
]
