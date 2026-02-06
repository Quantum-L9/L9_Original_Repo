"""
L9 SDK - Per-Agent API for L9 AIOS

Provides isolated SDK instances for each agent with automatic context injection.

Usage:
    from SDK import L9SDK

    # Each agent gets its own instance
    lcto_sdk = L9SDK(agent_id="l-cto", tenant_id="acme-corp")
    lcfo_sdk = L9SDK(agent_id="l-cfo", tenant_id="acme-corp")

    # Agent ID is auto-injected
    await lcto_sdk.run_task("Research async patterns")
    await lcto_sdk.query_memory("What did we learn?")

Version: 3.0.0
Breaking: Migrated from singleton facade to per-agent instances
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# Interface Classes (Keep existing P0/P1/P2 interfaces)
# =============================================================================


class WorldModelInterface:
    """Interface to L9 World Model - entity state and beliefs."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk
        self._service: Any | None = None

    async def _get_service(self) -> Any:
        """Lazy load world model service."""
        if self._service is None:
            try:
                from core.worldmodel.service import WorldModelService

                self._service = WorldModelService()
            except ImportError:
                logger.warning("WorldModelService not available")
        return self._service

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Get entity state from world model."""
        service = await self._get_service()
        if not service:
            return None
        return await service.get_entity(
            entity_id=entity_id, tenant_id=self._sdk.tenant_id
        )


class GovernanceInterface:
    """Interface to L9 Governance - approvals and permissions (P0)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk
        self._service: Any | None = None

    async def check_approval(self, action: str) -> bool:
        """Check if action is approved for this agent."""
        logger.info("Checking approval", agent_id=self._sdk.agent_id, action=action)
        return True  # Stub - implement with real governance service


class ObservabilityInterface:
    """Interface to L9 Observability - tracing and metrics (P0)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    def trace(self, event: str, **kwargs) -> None:
        """Emit a trace event."""
        logger.info(event, agent_id=self._sdk.agent_id, **kwargs)


class TaskQueueInterface:
    """Interface to L9 Task Queue - background jobs (P1)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def enqueue(self, task: str, payload: dict[str, Any] | None = None) -> str:
        """Enqueue a background task."""
        logger.info("Enqueue task", agent_id=self._sdk.agent_id, task=task)
        return f"task-{self._sdk.agent_id}-stub"


class CheckpointsInterface:
    """Interface to L9 Checkpoints - state persistence (P1)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def save(self, key: str, state: dict[str, Any]) -> None:
        """Save checkpoint state."""
        logger.info("Save checkpoint", agent_id=self._sdk.agent_id, key=key)

    async def load(self, key: str) -> dict[str, Any] | None:
        """Load checkpoint state."""
        logger.info("Load checkpoint", agent_id=self._sdk.agent_id, key=key)
        return None


class MCPInterface:
    """Interface to MCP tools and resources (P1)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def call_tool(self, server: str, tool: str, **kwargs) -> Any:
        """Call an MCP tool."""
        logger.info(
            "MCP tool call", agent_id=self._sdk.agent_id, server=server, tool=tool
        )
        return None


class LearningInterface:
    """Interface to L9 Learning - feedback and adaptation (P2)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def record_feedback(self, outcome: str, score: float) -> None:
        """Record learning feedback."""
        logger.info(
            "Record feedback", agent_id=self._sdk.agent_id, outcome=outcome, score=score
        )


class ComplianceInterface:
    """Interface to L9 Compliance - audit and regulatory (P2)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def log_audit(self, action: str, details: dict[str, Any]) -> None:
        """Log compliance audit entry."""
        logger.info("Audit log", agent_id=self._sdk.agent_id, action=action)


class ReasoningInterface:
    """Interface to L9 Reasoning - Bayesian and causal inference (P2)."""

    def __init__(self, sdk: L9SDK):
        self._sdk = sdk

    async def infer(self, hypothesis: str, evidence: list[str]) -> float:
        """Run inference on hypothesis given evidence."""
        logger.info(
            "Reasoning inference", agent_id=self._sdk.agent_id, hypothesis=hypothesis
        )
        return 0.5  # Stub


# =============================================================================
# L9 SDK - Per-Agent Instance
# =============================================================================


class L9SDK:
    """
    Per-agent SDK for L9 AIOS.

    Each agent gets an isolated SDK instance with automatic context injection.
    This replaces the previous singleton facade pattern for better isolation
    and multi-tenancy support.

    Args:
        agent_id: Unique agent identifier (e.g., "l-cto", "l-cfo")
        tenant_id: Tenant/organization ID (default: "default")
        auto_init: Whether to auto-initialize subsystems (default: True)

    Interfaces available:
        - world_model: Entity state and beliefs (P0)
        - governance: Approvals and permissions (P0)
        - observability: Tracing and metrics (P0)
        - tasks: Background job queue (P1)
        - checkpoints: State persistence (P1)
        - mcp: External MCP tools/resources (P1)
        - learning: Feedback and adaptation (P2)
        - compliance: Audit and regulatory (P2)
        - reasoning: Bayesian and causal inference (P2)
    """

    def __init__(
        self, agent_id: str, tenant_id: str = "default", auto_init: bool = True
    ):
        """Initialize per-agent SDK instance."""
        self.agent_id = agent_id
        self.tenant_id = tenant_id

        # Internal state (isolated per instance)
        self._mediator: Any | None = None
        self._tool_registry: Any | None = None
        self._memory_client: Any | None = None
        self._initialized = False

        # P0: Core interfaces
        self._world_model = WorldModelInterface(self)
        self._governance = GovernanceInterface(self)
        self._observability = ObservabilityInterface(self)

        # P1: Operational interfaces
        self._tasks = TaskQueueInterface(self)
        self._checkpoints = CheckpointsInterface(self)
        self._mcp = MCPInterface(self)

        # P2: Advanced interfaces
        self._learning = LearningInterface(self)
        self._compliance = ComplianceInterface(self)
        self._reasoning = ReasoningInterface(self)

        logger.info(
            "L9SDK initialized for agent", agent_id=agent_id, tenant_id=tenant_id
        )

        # Auto-initialize if requested
        if auto_init:
            asyncio.create_task(self.initialize())

    # =========================================================================
    # Interface Properties (same as before)
    # =========================================================================

    @property
    def world_model(self) -> WorldModelInterface:
        """P0: World Model interface."""
        return self._world_model

    @property
    def governance(self) -> GovernanceInterface:
        """P0: Governance interface."""
        return self._governance

    @property
    def observability(self) -> ObservabilityInterface:
        """P0: Observability interface."""
        return self._observability

    @property
    def tasks(self) -> TaskQueueInterface:
        """P1: Task Queue interface."""
        return self._tasks

    @property
    def checkpoints(self) -> CheckpointsInterface:
        """P1: Checkpoints interface."""
        return self._checkpoints

    @property
    def mcp(self) -> MCPInterface:
        """P1: MCP interface."""
        return self._mcp

    @property
    def learning(self) -> LearningInterface:
        """P2: Learning interface."""
        return self._learning

    @property
    def compliance(self) -> ComplianceInterface:
        """P2: Compliance interface."""
        return self._compliance

    @property
    def reasoning(self) -> ReasoningInterface:
        """P2: Reasoning interface."""
        return self._reasoning

    # =========================================================================
    # Core Methods (UPDATED: auto-inject agent_id/tenant_id)
    # =========================================================================

    async def initialize(
        self,
        memory_enabled: bool = True,
        tool_registry_enabled: bool = True,
        mediator_enabled: bool = True,
    ) -> None:
        """Initialize L9 subsystems for this agent."""
        if self._initialized:
            logger.warning("SDK already initialized", agent_id=self.agent_id)
            return

        # Initialize mediator
        if mediator_enabled:
            try:
                from core.coordination.agent_mediator import get_agent_mediator

                self._mediator = await get_agent_mediator()
                # Register this agent
                self._mediator.register_agent(self.agent_id, self)
                logger.info("Agent mediator initialized", agent_id=self.agent_id)
            except Exception as e:
                logger.warning(f"Failed to initialize mediator: {e}")

        # Initialize tool registry
        if tool_registry_enabled:
            try:
                from core.tools.registry_adapter import ExecutorToolRegistry

                self._tool_registry = ExecutorToolRegistry()
                logger.info("Tool registry initialized", agent_id=self.agent_id)
            except Exception as e:
                logger.warning(f"Failed to initialize tool registry: {e}")

        # Initialize memory client
        if memory_enabled:
            try:
                from memory.client import MemoryClient

                self._memory_client = MemoryClient()
                logger.info("Memory client initialized", agent_id=self.agent_id)
            except Exception as e:
                logger.warning(f"Failed to initialize memory client: {e}")

        self._initialized = True
        logger.info("SDK initialization complete", agent_id=self.agent_id)

    async def run_task(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> Any:
        """
        Run a task with this agent's context.

        Args:
            task: Task description
            context: Additional context
            timeout_seconds: Timeout in seconds

        Returns:
            Task result

        Note: agent_id is automatically injected from SDK instance
        """
        logger.info(
            "Running task", agent_id=self.agent_id, tenant_id=self.tenant_id, task=task
        )

        # Inject agent context
        full_context = {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            **(context or {}),
        }

        # Execute task (implementation depends on your runtime)
        if self._mediator:
            return await self._mediator.execute_task(
                task=task, context=full_context, timeout_seconds=timeout_seconds
            )
        raise RuntimeError(f"Mediator not initialized for {self.agent_id}")

    async def send_message(
        self,
        to_agent: str,
        message: dict[str, Any],
        message_type: str = "generic",
    ) -> str:
        """
        Send a message to another agent.

        Args:
            to_agent: Recipient agent ID
            message: Message payload
            message_type: Type of message

        Returns:
            Message ID

        Note: from_agent is automatically set to self.agent_id
        """
        if not self._mediator:
            raise RuntimeError("Mediator not initialized")

        return await self._mediator.send_message(
            from_agent=self.agent_id,  # Auto-injected
            to_agent=to_agent,
            message=message,
            message_type=message_type,
        )

    async def broadcast(
        self, message: dict[str, Any], message_type: str = "broadcast"
    ) -> list[str]:
        """
        Broadcast a message to all agents.

        Args:
            message: Message payload
            message_type: Type of message

        Returns:
            List of message IDs

        Note: from_agent is automatically set to self.agent_id
        """
        if not self._mediator:
            raise RuntimeError("Mediator not initialized")

        return await self._mediator.broadcast(
            from_agent=self.agent_id,  # Auto-injected
            message=message,
            message_type=message_type,
        )

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Note: agent_id is automatically injected
        """
        if not self._tool_registry:
            raise RuntimeError("Tool registry not initialized")

        logger.info(
            f"Executing tool: {tool_name}",
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
        )

        return await self._tool_registry.dispatch_tool_call(
            tool_id=tool_name,
            arguments=kwargs,
            agent_id=self.agent_id,  # Auto-injected
            tenant_id=self.tenant_id,  # Auto-injected
        )

    async def query_memory(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Query the memory substrate.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of memory entries

        Note: Automatically scoped to this agent's memories
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")

        logger.info(
            "Querying memory",
            query=query,
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
        )

        return await self._memory_client.search(
            query=query,
            agent_id=self.agent_id,  # Auto-scoped
            tenant_id=self.tenant_id,  # Auto-scoped
            limit=limit,
        )

    async def store_memory(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Store a memory entry for this agent.

        Args:
            content: Memory content
            metadata: Additional metadata

        Returns:
            Memory entry ID

        Note: agent_id is automatically injected
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")

        logger.info("Storing memory", agent_id=self.agent_id, tenant_id=self.tenant_id)

        return await self._memory_client.store(
            agent_id=self.agent_id,  # Auto-injected
            tenant_id=self.tenant_id,  # Auto-injected
            content=content,
            metadata=metadata or {},
        )

    def list_tools(self) -> list[str]:
        """List all available tools."""
        if not self._tool_registry:
            return []
        return list(getattr(self._tool_registry, "_registry", {}).keys())

    async def shutdown(self) -> None:
        """Gracefully shutdown this SDK instance."""
        logger.info("Shutting down SDK", agent_id=self.agent_id)

        # Unregister from mediator
        if self._mediator:
            self._mediator.unregister_agent(self.agent_id)

        # Close memory client
        if self._memory_client and hasattr(self._memory_client, "close"):
            await self._memory_client.close()

        self._initialized = False
        logger.info("SDK shutdown complete", agent_id=self.agent_id)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Legacy class name (prefer L9SDK)
L9Facade = L9SDK

# Global instance for simple use cases (prefer per-agent instantiation)
_sdk_instance: L9SDK | None = None


async def get_l9_facade(agent_id: str = "default", tenant_id: str = "default") -> L9SDK:
    """
    Get or create an SDK instance.

    DEPRECATED: Prefer creating per-agent instances directly:
        sdk = L9SDK(agent_id="my-agent")

    This function exists for backward compatibility.
    """
    global _sdk_instance
    if _sdk_instance is None:
        _sdk_instance = L9SDK(agent_id=agent_id, tenant_id=tenant_id, auto_init=False)
        await _sdk_instance.initialize()
    return _sdk_instance


# Alias for consistency
get_l9_sdk = get_l9_facade


async def close_l9_facade() -> None:
    """Close the global SDK instance."""
    global _sdk_instance
    if _sdk_instance is not None:
        await _sdk_instance.shutdown()
        _sdk_instance = None


# Alias
close_l9_sdk = close_l9_facade


# =============================================================================
# Convenience Functions (use global instance)
# =============================================================================


async def run_task(task: str, **kwargs) -> Any:
    """
    Convenience function to run a task via global SDK instance.

    For per-agent isolation, use:
        sdk = L9SDK(agent_id="my-agent")
        await sdk.run_task(task)
    """
    sdk = await get_l9_facade()
    return await sdk.run_task(task, **kwargs)


async def execute_tool(tool_name: str, **kwargs) -> Any:
    """Convenience function to execute a tool via global SDK instance."""
    sdk = await get_l9_facade()
    return await sdk.execute_tool(tool_name, **kwargs)


async def query_memory(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Convenience function to query memory via global SDK instance."""
    sdk = await get_l9_facade()
    return await sdk.query_memory(query, limit=limit)
