"""
L9 Facade - Simplified API for L9 AIOS
======================================

Implements the Facade design pattern to provide a simple, unified interface
to the complex L9 AIOS subsystems. This makes it easier for developers to
interact with L9 without needing to understand all internal details.

Forked from PR #53 with L9 singleton integration (uses @register_singleton).

Benefits:
- Simple, intuitive API for common operations
- Hides complexity of internal subsystems
- Reduces learning curve for new developers
- Provides sensible defaults
- Easier to maintain and evolve internal architecture

Usage:
    from core.facade import L9Facade, get_l9_facade

    # Get singleton facade instance (via L9 registry)
    l9 = await get_l9_facade()

    # Initialize with defaults
    await l9.initialize()

    # Run a task with L-CTO agent
    result = await l9.run_task(
        "Research async patterns in Python",
        agent="l-cto"
    )

    # Query memory
    memories = await l9.query_memory(
        "What did we learn about async patterns?",
        agent_id="l-cto"
    )

    # Execute a tool
    result = await l9.execute_tool(
        "slack_send",
        channel="#general",
        message="Task complete!"
    )

Version: 1.0.0
Source: Forked from PR #53, aligned with L9 singleton infrastructure
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Facade",
    "module_version": "1.0.0",
    "created_by": "L9 Design Patterns Initiative",
    "created_at": "2026-01-24T19:30:00Z",
    "updated_at": "2026-01-24T19:30:00Z",
    "layer": "core",
    "domain": "api_facade",
    "module_name": "l9_facade",
    "type": "service",
    "status": "active",
    "source": "Forked from PR #53 with L9 singleton integration",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["memory_substrate"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from typing import Any

import structlog

from core.singleton_auto_registry import register_singleton, register_singleton_closer
from core.singleton_registry import SingletonLifecycle

logger = structlog.get_logger(__name__)


# =============================================================================
# L9 Facade Service
# =============================================================================


class L9Facade:
    """
    Simplified facade for L9 AIOS.

    Provides a clean, simple API for common L9 operations without
    requiring deep knowledge of internal subsystems.

    This is a singleton service - use get_l9_facade() to obtain instance.
    """

    def __init__(self):
        """Initialize L9 facade with default configuration."""
        self._agents: dict[str, Any] = {}
        self._mediator: Any | None = None
        self._tool_registry: Any | None = None
        self._memory_client: Any | None = None
        self._initialized = False

        logger.info("L9Facade initialized")

    async def initialize(
        self,
        memory_enabled: bool = True,
        tool_registry_enabled: bool = True,
        mediator_enabled: bool = True,
    ) -> None:
        """
        Initialize L9 subsystems.

        Args:
            memory_enabled: Whether to enable memory substrate
            tool_registry_enabled: Whether to enable tool registry
            mediator_enabled: Whether to enable agent mediator
        """
        if self._initialized:
            logger.warning("L9Facade already initialized")
            return

        # Initialize mediator (using L9 singleton)
        if mediator_enabled:
            try:
                from core.coordination.agent_mediator import get_agent_mediator

                self._mediator = await get_agent_mediator()
                logger.info("Agent mediator initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize mediator: {e}")

        # Initialize tool registry (using L9 singleton if available)
        if tool_registry_enabled:
            try:
                from core.singleton_registry import get_singleton_registry

                registry = get_singleton_registry()
                self._tool_registry = registry.get("tool_registry")
                if self._tool_registry:
                    logger.info("Tool registry initialized from singleton registry")
                else:
                    # Fallback: direct import
                    from core.tools.registry_adapter import ExecutorToolRegistry

                    self._tool_registry = ExecutorToolRegistry()
                    logger.info("Tool registry initialized directly")
            except Exception as e:
                logger.warning(f"Failed to initialize tool registry: {e}")

        # Initialize memory client
        if memory_enabled:
            try:
                from memory.client import MemoryClient

                self._memory_client = MemoryClient()
                logger.info("Memory client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize memory client: {e}")

        self._initialized = True
        logger.info("L9Facade initialization complete")

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent with L9.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self._agents[agent_id] = agent
        if self._mediator:
            self._mediator.register_agent(agent_id, agent)
        logger.info(f"Agent registered: {agent_id}")

    async def run_task(
        self,
        task: str,
        agent: str = "l-cto",
        context: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> Any:
        """
        Run a task with a specified agent.

        Args:
            task: Task description
            agent: Agent ID to run the task (default: "l-cto")
            context: Additional context for the task
            timeout_seconds: Timeout in seconds (None = no timeout)

        Returns:
            Task result (PacketEnvelope or similar)

        Raises:
            ValueError: If agent not found
            TimeoutError: If task exceeds timeout
        """
        if agent not in self._agents:
            raise ValueError(
                f"Agent '{agent}' not registered. Available: {list(self._agents.keys())}"
            )

        logger.info(f"Running task with {agent}", task=task)

        agent_instance = self._agents[agent]

        # Run with timeout if specified
        if timeout_seconds:
            try:
                async with asyncio.timeout(timeout_seconds):
                    return await agent_instance.run(task, context or {})
            except TimeoutError as e:
                raise TimeoutError(
                    f"Task exceeded timeout of {timeout_seconds}s"
                ) from e
        else:
            return await agent_instance.run(task, context or {})

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: dict[str, Any],
        message_type: str = "generic",
    ) -> str:
        """
        Send a message between agents.

        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            message: Message payload
            message_type: Type of message

        Returns:
            Message ID

        Raises:
            RuntimeError: If mediator not initialized
        """
        if not self._mediator:
            raise RuntimeError("Mediator not initialized")

        return await self._mediator.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message=message,
            message_type=message_type,
        )

    async def broadcast(
        self, from_agent: str, message: dict[str, Any], message_type: str = "broadcast"
    ) -> list[str]:
        """
        Broadcast a message to all agents.

        Args:
            from_agent: Sender agent ID
            message: Message payload
            message_type: Type of message

        Returns:
            List of message IDs

        Raises:
            RuntimeError: If mediator not initialized
        """
        if not self._mediator:
            raise RuntimeError("Mediator not initialized")

        return await self._mediator.broadcast(
            from_agent=from_agent, message=message, message_type=message_type
        )

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If tool registry not initialized
            ValueError: If tool not found
        """
        if not self._tool_registry:
            raise RuntimeError("Tool registry not initialized")

        logger.info(f"Executing tool: {tool_name}")

        # Execute tool via registry
        return await self._tool_registry.dispatch_tool_call(
            tool_id=tool_name, arguments=kwargs, agent_id="l9-facade"
        )

    async def query_memory(
        self, query: str, agent_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Query the memory substrate.

        Args:
            query: Search query
            agent_id: Filter by agent ID (None = all agents)
            limit: Maximum number of results

        Returns:
            List of memory entries

        Raises:
            RuntimeError: If memory client not initialized
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")

        logger.info("Querying memory", query=query, agent_id=agent_id)

        # Query memory
        return await self._memory_client.search(
            query=query, agent_id=agent_id, limit=limit
        )

    async def store_memory(
        self, agent_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Store a memory entry.

        Args:
            agent_id: Agent ID
            content: Memory content
            metadata: Additional metadata

        Returns:
            Memory entry ID

        Raises:
            RuntimeError: If memory client not initialized
        """
        if not self._memory_client:
            raise RuntimeError("Memory client not initialized")

        logger.info(f"Storing memory for {agent_id}")

        return await self._memory_client.store(
            agent_id=agent_id, content=content, metadata=metadata or {}
        )

    def list_agents(self) -> list[str]:
        """
        List all registered agents.

        Returns:
            List of agent IDs
        """
        return list(self._agents.keys())

    def list_tools(self) -> list[str]:
        """
        List all available tools.

        Returns:
            List of tool names
        """
        if not self._tool_registry:
            return []
        return list(getattr(self._tool_registry, "_registry", {}).keys())

    def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        """
        Get status of an agent.

        Args:
            agent_id: Agent to check

        Returns:
            Agent status dictionary
        """
        if agent_id not in self._agents:
            return {"exists": False}

        status = {"exists": True, "online": False, "queued_messages": 0}

        if self._mediator:
            status["online"] = self._mediator.get_agent_status(agent_id)
            status["queued_messages"] = self._mediator.get_queued_message_count(
                agent_id
            )

        return status

    async def shutdown(self) -> None:
        """Gracefully shutdown L9 and all subsystems."""
        logger.info("Shutting down L9Facade")

        # Unregister all agents
        for agent_id in list(self._agents.keys()):
            if self._mediator:
                self._mediator.unregister_agent(agent_id)

        self._agents.clear()

        # Close memory client
        if self._memory_client and hasattr(self._memory_client, "close"):
            await self._memory_client.close()

        self._initialized = False
        logger.info("L9Facade shutdown complete")


# =============================================================================
# Singleton Registration (L9 Auto-Registry Pattern)
# =============================================================================

# Module-level instance (initialized lazily)
_facade_instance: L9Facade | None = None


@register_singleton(
    category="core",
    lifecycle=SingletonLifecycle.LAZY,
    dependencies=["agent_mediator"],
    description="Simplified unified API facade for L9 AIOS operations",
)
async def get_l9_facade() -> L9Facade:
    """
    Get the singleton L9Facade instance.

    Uses L9's @register_singleton for proper lifecycle management.

    Returns:
        The global L9Facade instance
    """
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = L9Facade()
    return _facade_instance


@register_singleton_closer("l9_facade")
async def close_l9_facade() -> None:
    """Close the L9Facade singleton."""
    global _facade_instance
    if _facade_instance is not None:
        await _facade_instance.shutdown()
        _facade_instance = None
        logger.info("L9Facade singleton closed")


# =============================================================================
# Convenience Functions for Quick Access
# =============================================================================


async def run_task(task: str, agent: str = "l-cto", **kwargs) -> Any:
    """
    Quick function to run a task with L9.

    Args:
        task: Task description
        agent: Agent ID (default: "l-cto")
        **kwargs: Additional arguments

    Returns:
        Task result
    """
    l9 = await get_l9_facade()
    if not l9._initialized:
        await l9.initialize()
    return await l9.run_task(task, agent, **kwargs)


async def execute_tool(tool_name: str, **kwargs) -> Any:
    """
    Quick function to execute a tool.

    Args:
        tool_name: Tool to execute
        **kwargs: Tool arguments

    Returns:
        Tool result
    """
    l9 = await get_l9_facade()
    if not l9._initialized:
        await l9.initialize()
    return await l9.execute_tool(tool_name, **kwargs)


async def query_memory(query: str, agent_id: str | None = None) -> list[dict[str, Any]]:
    """
    Quick function to query memory.

    Args:
        query: Search query
        agent_id: Filter by agent (optional)

    Returns:
        Memory results
    """
    l9 = await get_l9_facade()
    if not l9._initialized:
        await l9.initialize()
    return await l9.query_memory(query, agent_id)
