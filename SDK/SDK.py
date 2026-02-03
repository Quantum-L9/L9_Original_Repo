"""
L9 SDK - Simplified API for L9 AIOS
===================================

The canonical SDK for L9 Secure AI OS. Provides a simple, unified interface
to complex L9 subsystems.

Benefits:
- Simple, intuitive API for common operations
- Hides complexity of internal subsystems
- Reduces learning curve for new developers
- Provides sensible defaults
- Easier to maintain and evolve internal architecture

Usage:
    from SDK import L9, get_l9

    # Get singleton instance (via L9 registry)
    l9 = await get_l9()

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

Version: 2.1.0
Location: SDK/ (root-level)
Relocated from: l9/facade.py → core/facade/ (GMP-134, GMP-135)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 SDK Facade",
    "module_version": "2.0.0",
    "created_by": "L9 Design Patterns Initiative",
    "created_at": "2026-01-24T19:30:00Z",
    "updated_at": "2026-02-02T18:50:00Z",
    "layer": "sdk",
    "domain": "public_api",
    "module_name": "facade",
    "type": "service",
    "status": "active",
    "source": "Relocated from core/facade/ (GMP-134) for cleaner SDK access",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["memory_substrate"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api", "agents", "services"],
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
# P0: World Model Interface
# =============================================================================


class WorldModelInterface:
    """Interface to L9 World Model - entity state and beliefs."""

    def __init__(self, facade: L9Facade):
        self._facade = facade
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
        return await service.get_entity(entity_id)

    async def update_belief(
        self, entity_id: str, belief: dict[str, Any], confidence: float = 0.8
    ) -> bool:
        """Update belief about an entity."""
        service = await self._get_service()
        if not service:
            return False
        return await service.update_belief(entity_id, belief, confidence)

    async def get_relationships(
        self, entity_id: str, relationship_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get entity relationships from world model graph."""
        service = await self._get_service()
        if not service:
            return []
        return await service.get_relationships(entity_id, relationship_type)

    async def query(self, cypher_query: str) -> list[dict[str, Any]]:
        """Execute raw Cypher query on world model."""
        service = await self._get_service()
        if not service:
            return []
        return await service.query(cypher_query)


# =============================================================================
# P0: Governance Interface
# =============================================================================


class GovernanceInterface:
    """Interface to L9 Governance - approvals and permissions."""

    def __init__(self, facade: L9Facade):
        self._facade = facade
        self._approval_manager: Any | None = None

    async def _get_manager(self) -> Any:
        """Lazy load approval manager."""
        if self._approval_manager is None:
            try:
                from core.governance.approval_manager import ApprovalManager

                self._approval_manager = ApprovalManager()
            except ImportError:
                logger.warning("ApprovalManager not available")
        return self._approval_manager

    async def request_approval(
        self,
        action: str,
        context: dict[str, Any] | None = None,
        requester: str = "l9-facade",
    ) -> str | None:
        """Request human approval for an action."""
        manager = await self._get_manager()
        if not manager:
            return None
        return await manager.request_approval(
            action=action, context=context or {}, requester=requester
        )

    async def check_approval(self, approval_id: str) -> dict[str, Any]:
        """Check approval status."""
        manager = await self._get_manager()
        if not manager:
            return {"status": "unknown", "error": "manager_unavailable"}
        return await manager.get_approval_status(approval_id)

    async def get_permissions(self, agent_id: str) -> list[str]:
        """Get current permissions for an agent."""
        manager = await self._get_manager()
        if not manager:
            return []
        return await manager.get_agent_permissions(agent_id)

    async def is_action_allowed(self, action: str, agent_id: str) -> bool:
        """Check if an action is allowed for an agent."""
        manager = await self._get_manager()
        if not manager:
            return False
        return await manager.is_allowed(action, agent_id)


# =============================================================================
# P0: Observability Interface
# =============================================================================


class ObservabilityInterface:
    """Interface to L9 Observability - tracing and metrics."""

    def __init__(self, facade: L9Facade):
        self._facade = facade

    def get_trace_context(self) -> dict[str, str]:
        """Get current trace context (trace_id, span_id)."""
        try:
            from core.observability.context import get_trace_context

            return get_trace_context()
        except ImportError:
            return {"trace_id": "", "span_id": ""}

    async def emit_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        level: str = "info",
    ) -> None:
        """Emit a structured event."""
        log_fn = getattr(logger, level, logger.info)
        log_fn(event_name, **payload)

    def get_metrics(self) -> dict[str, Any]:
        """Get current Prometheus metrics."""
        try:
            from core.observability.metrics import get_metrics_snapshot

            return get_metrics_snapshot()
        except ImportError:
            return {}

    def create_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        """Create a new trace span."""
        try:
            from core.observability.tracing import create_span

            return create_span(name, attributes or {})
        except ImportError:
            return None


# =============================================================================
# P1: Task Queue Interface
# =============================================================================


class TaskQueueInterface:
    """Interface to L9 Task Queue - background jobs."""

    def __init__(self, facade: L9Facade):
        self._facade = facade
        self._task_queue: Any | None = None

    async def _get_queue(self) -> Any:
        """Lazy load task queue."""
        if self._task_queue is None:
            try:
                from runtime.task_queue import get_task_queue

                self._task_queue = await get_task_queue()
            except ImportError:
                logger.warning("TaskQueue not available")
        return self._task_queue

    async def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any] | None = None,
        priority: str = "normal",
        delay_seconds: int = 0,
    ) -> str | None:
        """Enqueue a background task."""
        queue = await self._get_queue()
        if not queue:
            return None
        return await queue.enqueue(
            task_name=task_name,
            payload=payload or {},
            priority=priority,
            delay_seconds=delay_seconds,
        )

    async def get_status(self, task_id: str) -> dict[str, Any]:
        """Get task status."""
        queue = await self._get_queue()
        if not queue:
            return {"status": "unknown", "error": "queue_unavailable"}
        return await queue.get_task_status(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a queued task."""
        queue = await self._get_queue()
        if not queue:
            return False
        return await queue.cancel_task(task_id)

    async def list_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        """List pending tasks."""
        queue = await self._get_queue()
        if not queue:
            return []
        return await queue.list_pending(limit=limit)


# =============================================================================
# P1: Checkpoints Interface
# =============================================================================


class CheckpointsInterface:
    """Interface to L9 Checkpoints - state persistence."""

    def __init__(self, facade: L9Facade):
        self._facade = facade
        self._checkpoint_manager: Any | None = None

    async def _get_manager(self) -> Any:
        """Lazy load checkpoint manager."""
        if self._checkpoint_manager is None:
            try:
                from memory.checkpoint_manager import CheckpointManager

                self._checkpoint_manager = CheckpointManager()
            except ImportError:
                logger.warning("CheckpointManager not available")
        return self._checkpoint_manager

    async def save(
        self,
        checkpoint_id: str,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a checkpoint."""
        manager = await self._get_manager()
        if not manager:
            return False
        return await manager.save_checkpoint(
            checkpoint_id=checkpoint_id, state=state, metadata=metadata or {}
        )

    async def restore(self, checkpoint_id: str) -> dict[str, Any] | None:
        """Restore from a checkpoint."""
        manager = await self._get_manager()
        if not manager:
            return None
        return await manager.restore_checkpoint(checkpoint_id)

    async def list_checkpoints(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """List available checkpoints."""
        manager = await self._get_manager()
        if not manager:
            return []
        return await manager.list_checkpoints(agent_id=agent_id, limit=limit)

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        manager = await self._get_manager()
        if not manager:
            return False
        return await manager.delete_checkpoint(checkpoint_id)


# =============================================================================
# P1: MCP Interface
# =============================================================================


class MCPInterface:
    """Interface to MCP (Model Context Protocol) - external tools/resources."""

    def __init__(self, facade: L9Facade):
        self._facade = facade
        self._mcp_client: Any | None = None

    async def _get_client(self) -> Any:
        """Lazy load MCP client."""
        if self._mcp_client is None:
            try:
                from runtime.mcp_client import get_mcp_client

                self._mcp_client = await get_mcp_client()
            except ImportError:
                logger.warning("MCP client not available")
        return self._mcp_client

    async def call_tool(
        self,
        server: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call an MCP tool."""
        client = await self._get_client()
        if not client:
            return {"error": "mcp_unavailable"}
        return await client.call_tool(
            server=server, tool_name=tool_name, arguments=arguments or {}
        )

    async def list_servers(self) -> list[str]:
        """List available MCP servers."""
        client = await self._get_client()
        if not client:
            return []
        return await client.list_servers()

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """List tools available on an MCP server."""
        client = await self._get_client()
        if not client:
            return []
        return await client.list_tools(server)

    async def list_resources(self, server: str) -> list[dict[str, Any]]:
        """List resources available on an MCP server."""
        client = await self._get_client()
        if not client:
            return []
        return await client.list_resources(server)

    async def fetch_resource(self, server: str, uri: str) -> Any:
        """Fetch an MCP resource."""
        client = await self._get_client()
        if not client:
            return None
        return await client.fetch_resource(server=server, uri=uri)


# =============================================================================
# P2: Learning Interface
# =============================================================================


class LearningInterface:
    """Interface to L9 Learning - feedback and adaptation."""

    def __init__(self, facade: L9Facade):
        self._facade = facade

    async def submit_feedback(
        self,
        feedback_type: str,
        content: str,
        context: dict[str, Any] | None = None,
        rating: int | None = None,
    ) -> str | None:
        """Submit human feedback for learning."""
        try:
            from core.learning.feedback import submit_feedback

            return await submit_feedback(
                feedback_type=feedback_type,
                content=content,
                context=context or {},
                rating=rating,
            )
        except ImportError:
            logger.warning("Learning module not available")
            return None

    async def get_learning_status(self) -> dict[str, Any]:
        """Get current learning/adaptation status."""
        try:
            from core.learning.status import get_learning_status

            return await get_learning_status()
        except ImportError:
            return {"status": "unavailable"}

    async def get_improvement_suggestions(
        self, domain: str | None = None
    ) -> list[dict[str, Any]]:
        """Get AI-generated improvement suggestions."""
        try:
            from core.learning.suggestions import get_suggestions

            return await get_suggestions(domain=domain)
        except ImportError:
            return []


# =============================================================================
# P2: Compliance Interface
# =============================================================================


class ComplianceInterface:
    """Interface to L9 Compliance - audit and regulatory."""

    def __init__(self, facade: L9Facade):
        self._facade = facade

    async def get_audit_log(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        agent_id: str | None = None,
        action_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries."""
        try:
            from core.compliance.audit_log import get_audit_log

            return await get_audit_log(
                start_time=start_time,
                end_time=end_time,
                agent_id=agent_id,
                action_type=action_type,
                limit=limit,
            )
        except ImportError:
            return []

    async def check_compliance(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Pre-check if an action is compliant."""
        try:
            from core.compliance.checker import check_compliance

            return await check_compliance(action=action, context=context or {})
        except ImportError:
            return {"compliant": True, "checks": [], "warnings": []}

    async def generate_compliance_report(
        self, report_type: str = "summary"
    ) -> dict[str, Any]:
        """Generate a compliance report."""
        try:
            from core.compliance.audit_reporter import generate_report

            return await generate_report(report_type=report_type)
        except ImportError:
            return {"error": "reporter_unavailable"}


# =============================================================================
# P2: Reasoning Interface
# =============================================================================


class ReasoningInterface:
    """Interface to L9 Reasoning - Bayesian and causal inference."""

    def __init__(self, facade: L9Facade):
        self._facade = facade

    async def probabilistic_query(
        self, query: str, evidence: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a probabilistic query."""
        try:
            from core.bayesian.probabilistic_engine import probabilistic_query

            return await probabilistic_query(query=query, evidence=evidence or {})
        except ImportError:
            return {"error": "bayesian_engine_unavailable"}

    async def causal_analysis(
        self,
        cause: str,
        effect: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform causal analysis between two events."""
        try:
            from core.reasoning.toth_engine import causal_analysis

            return await causal_analysis(
                cause=cause, effect=effect, context=context or {}
            )
        except ImportError:
            return {"error": "reasoning_engine_unavailable"}

    async def update_prior(
        self, belief_id: str, new_evidence: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a prior belief with new evidence (Bayesian update)."""
        try:
            from core.bayesian.uncertainty import update_prior

            return await update_prior(belief_id=belief_id, evidence=new_evidence)
        except ImportError:
            return {"error": "bayesian_update_unavailable"}


# =============================================================================
# L9 Facade Service
# =============================================================================


class L9Facade:
    """
    Simplified facade for L9 AIOS.

    Provides a clean, simple API for common L9 operations without
    requiring deep knowledge of internal subsystems.

    This is a singleton service - use get_l9_facade() to obtain instance.

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

    def __init__(self):
        """Initialize L9 facade with default configuration."""
        self._agents: dict[str, Any] = {}
        self._mediator: Any | None = None
        self._tool_registry: Any | None = None
        self._memory_client: Any | None = None
        self._initialized = False

        # P0: Core interfaces (Must Have)
        self._world_model = WorldModelInterface(self)
        self._governance = GovernanceInterface(self)
        self._observability = ObservabilityInterface(self)

        # P1: Operational interfaces (Should Have)
        self._tasks = TaskQueueInterface(self)
        self._checkpoints = CheckpointsInterface(self)
        self._mcp = MCPInterface(self)

        # P2: Advanced interfaces (Nice to Have)
        self._learning = LearningInterface(self)
        self._compliance = ComplianceInterface(self)
        self._reasoning = ReasoningInterface(self)

        logger.info("L9Facade initialized with P0/P1/P2 interfaces")

    # =========================================================================
    # Interface Properties
    # =========================================================================

    @property
    def world_model(self) -> WorldModelInterface:
        """P0: World Model interface - entity state and beliefs."""
        return self._world_model

    @property
    def governance(self) -> GovernanceInterface:
        """P0: Governance interface - approvals and permissions."""
        return self._governance

    @property
    def observability(self) -> ObservabilityInterface:
        """P0: Observability interface - tracing and metrics."""
        return self._observability

    @property
    def tasks(self) -> TaskQueueInterface:
        """P1: Task Queue interface - background jobs."""
        return self._tasks

    @property
    def checkpoints(self) -> CheckpointsInterface:
        """P1: Checkpoints interface - state persistence."""
        return self._checkpoints

    @property
    def mcp(self) -> MCPInterface:
        """P1: MCP interface - external tools/resources."""
        return self._mcp

    @property
    def learning(self) -> LearningInterface:
        """P2: Learning interface - feedback and adaptation."""
        return self._learning

    @property
    def compliance(self) -> ComplianceInterface:
        """P2: Compliance interface - audit and regulatory."""
        return self._compliance

    @property
    def reasoning(self) -> ReasoningInterface:
        """P2: Reasoning interface - Bayesian and causal inference."""
        return self._reasoning

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
    if _facade_instance is None:  # nosemgrep: l9-singleton-requires-lock
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-047",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.coordination.agent_mediator",
        "core.singleton_auto_registry",
        "core.singleton_registry",
        "core.tools.registry_adapter",
        "memory.client",
    ],
    "tags": ["async", "core", "foundation", "logging", "messaging", "queue", "service"],
    "keywords": [
        "agent",
        "agents",
        "aios",
        "api",
        "async",
        "await",
        "broadcast",
        "close",
    ],
    "business_value": "Implements the Facade design pattern to provide a simple, unified interface to the complex L9 AIOS subsystems. This makes it easier for developers to interact with L9 without needing to understand all",
    "last_modified": "2026-01-24T15:21:11Z",
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
