"""
L9 Core Tools - Base Registry
Version: 2.1.0

Universal in-memory tool registry for ALL L9 tools (research + L-CTO + custom).
NO database persistence - tools are registered at startup.

Architecture:
- This is the BASE STORAGE layer (singleton via get_tool_registry())
- ExecutorToolRegistry in registry_adapter.py WRAPS this for governance + OpenAI format
- L tools are registered via register_l_tools() at server startup
- Research tools (Perplexity, HTTP, Mock) auto-registered on first access

Production-ready features (v2.1.0):
- Time-based sliding window rate limiting
- Tool schema support for OpenAI function calling
- Async execution with timeout handling
"""

import asyncio
import structlog
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ToolType(str, Enum):
    """Types of available tools."""

    SEARCH = "search"
    HTTP = "http"
    PERPLEXITY = "perplexity"
    MOCK = "mock"
    CUSTOM = "custom"


class ToolSchema(BaseModel):
    """JSON Schema for tool parameters (OpenAI function calling compatible)."""

    type: str = Field(default="object")
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class ToolMetadata(BaseModel):
    """
    Metadata for a registered tool.

    Describes tool capabilities, access control, and rate limits.
    """

    id: str = Field(..., description="Unique tool identifier (canonical identity)")
    name: str = Field(..., description="Human-readable name (display only)")
    description: str = Field("", description="Tool description")
    tool_type: ToolType = Field(..., description="Type of tool")
    allowed_roles: list[str] = Field(
        default=["researcher"], description="Roles allowed to use this tool"
    )
    rate_limit: int = Field(
        default=60, description="Max calls per minute (sliding window)"
    )
    timeout_seconds: int = Field(default=30, description="Timeout for tool execution")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    requires_api_key: bool = Field(
        default=False, description="Whether tool requires API key"
    )
    input_schema: Optional[ToolSchema] = Field(
        default=None, description="JSON Schema for tool parameters"
    )

    class Config:
        use_enum_values = True


class RateLimitWindow:
    """
    Sliding window rate limiter.

    Tracks calls within a time window and enforces limits.
    """

    def __init__(self, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Size of sliding window
        """
        self._window_seconds = window_seconds
        self._calls: dict[str, list[datetime]] = defaultdict(list)

    def check_and_increment(self, key: str, limit: int) -> bool:
        """
        Check if under rate limit and increment if so.

        Args:
            key: Rate limit key (e.g., tool_id)
            limit: Maximum calls per window

        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._window_seconds)

        # Prune old calls
        self._calls[key] = [t for t in self._calls[key] if t > cutoff]

        # Check limit
        if len(self._calls[key]) >= limit:
            return False

        # Record call
        self._calls[key].append(now)
        return True

    def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining calls in current window."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._window_seconds)
        current = len([t for t in self._calls[key] if t > cutoff])
        return max(0, limit - current)

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limits for a key or all keys."""
        if key:
            self._calls[key] = []
        else:
            self._calls.clear()


class ToolRegistry:
    """
    In-memory registry of available tools.

    Stores tool metadata and tool instances for execution.
    No database persistence - tools are registered at runtime.

    Production features:
    - Time-based sliding window rate limiting (1-minute window)
    - Async tool execution with timeout
    - Tool schema extraction for function calling
    """

    def __init__(self, rate_window_seconds: int = 60):
        """
        Initialize empty registry.

        Args:
            rate_window_seconds: Sliding window for rate limiting
        """
        self._tools: dict[str, ToolMetadata] = {}
        self._executors: dict[str, Any] = {}  # Tool instances
        self._rate_limiter = RateLimitWindow(rate_window_seconds)

    def register(
        self,
        metadata: ToolMetadata,
        executor: Optional[Any] = None,
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            metadata: Tool metadata
            executor: Optional tool instance for execution
        """
        self._tools[metadata.id] = metadata
        if executor:
            self._executors[metadata.id] = executor

        logger.info(f"Registered tool: {metadata.name} ({metadata.id})")

    def get(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get tool metadata by ID."""
        return self._tools.get(tool_id)

    def get_executor(self, tool_id: str) -> Optional[Any]:
        """Get tool executor instance by ID."""
        return self._executors.get(tool_id)

    def get_by_type(self, tool_type: ToolType) -> list[ToolMetadata]:
        """Get all tools of a specific type."""
        return [
            t for t in self._tools.values() if t.tool_type == tool_type and t.enabled
        ]

    def get_for_role(self, role: str) -> list[ToolMetadata]:
        """Get all tools available for a role."""
        return [
            t for t in self._tools.values() if role in t.allowed_roles and t.enabled
        ]

    def list_all(self) -> list[ToolMetadata]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_enabled(self) -> list[ToolMetadata]:
        """List only enabled tools."""
        return [t for t in self._tools.values() if t.enabled]

    def disable(self, tool_id: str) -> None:
        """Disable a tool."""
        if tool_id in self._tools:
            self._tools[tool_id].enabled = False
            logger.info(f"Disabled tool: {tool_id}")

    def enable(self, tool_id: str) -> None:
        """Enable a tool."""
        if tool_id in self._tools:
            self._tools[tool_id].enabled = True
            logger.info(f"Enabled tool: {tool_id}")

    def check_rate_limit(self, tool_id: str) -> bool:
        """
        Check if tool is within rate limit (sliding window).

        Uses time-based sliding window rate limiting.

        Returns:
            True if allowed (and increments counter), False if rate limited
        """
        metadata = self._tools.get(tool_id)
        if not metadata:
            return False

        return self._rate_limiter.check_and_increment(tool_id, metadata.rate_limit)

    def get_rate_limit_remaining(self, tool_id: str) -> int:
        """Get remaining calls in current rate limit window."""
        metadata = self._tools.get(tool_id)
        if not metadata:
            return 0
        return self._rate_limiter.get_remaining(tool_id, metadata.rate_limit)

    def reset_rate_limits(self, tool_id: Optional[str] = None) -> None:
        """Reset rate limit counters for a tool or all tools."""
        self._rate_limiter.reset(tool_id)

    def get_tool_schema(self, tool_id: str) -> dict[str, Any]:
        """
        Get OpenAI function calling schema for a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            JSON Schema dict for function parameters
        """
        metadata = self._tools.get(tool_id)
        if not metadata:
            return {"type": "object", "properties": {}}

        if metadata.input_schema:
            return metadata.input_schema.model_dump()

        # Return default schema
        return {"type": "object", "properties": {}}

    async def execute_tool(
        self,
        tool_id: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a tool with timeout handling.

        Args:
            tool_id: Tool to execute
            arguments: Arguments for tool

        Returns:
            Dict with success, result/error, duration_ms
        """
        start_time = datetime.utcnow()

        metadata = self._tools.get(tool_id)
        if not metadata:
            return {
                "success": False,
                "error": f"Tool not found: {tool_id}",
                "duration_ms": 0,
            }

        if not metadata.enabled:
            return {
                "success": False,
                "error": f"Tool is disabled: {tool_id}",
                "duration_ms": 0,
            }

        # Check rate limit
        if not self.check_rate_limit(tool_id):
            return {
                "success": False,
                "error": f"Rate limit exceeded for {tool_id}",
                "duration_ms": 0,
            }

        executor = self._executors.get(tool_id)
        if not executor:
            return {
                "success": False,
                "error": f"No executor for tool: {tool_id}",
                "duration_ms": 0,
            }

        try:
            # Execute with timeout
            timeout = metadata.timeout_seconds

            if hasattr(executor, "execute"):
                if asyncio.iscoroutinefunction(executor.execute):
                    result = await asyncio.wait_for(
                        executor.execute(**arguments),
                        timeout=timeout,
                    )
                else:
                    # Wrap sync in executor
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, lambda: executor.execute(**arguments)
                        ),
                        timeout=timeout,
                    )
            elif callable(executor):
                if asyncio.iscoroutinefunction(executor):
                    result = await asyncio.wait_for(
                        executor(**arguments),
                        timeout=timeout,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: executor(**arguments)),
                        timeout=timeout,
                    )
            else:
                return {
                    "success": False,
                    "error": f"Executor not callable: {tool_id}",
                    "duration_ms": 0,
                }

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(f"Tool {tool_id} completed in {duration_ms}ms")

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
            }

        except asyncio.TimeoutError:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.warning(f"Tool {tool_id} timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Tool execution timed out after {timeout}s",
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.exception(f"Tool {tool_id} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
            }


# Singleton instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _initialize_default_tools(_registry)
    return _registry


def _initialize_default_tools(registry: ToolRegistry) -> None:
    """Initialize default tools in registry with schemas."""
    from services.research.tools.tool_wrappers import (
        PerplexityTool,
        HTTPTool,
        MockSearchTool,
    )

    # Perplexity Search
    perplexity_meta = ToolMetadata(
        id="perplexity_search",
        name="Perplexity Search",
        description="Search and synthesize information using Perplexity AI",
        tool_type=ToolType.PERPLEXITY,
        allowed_roles=["researcher", "planner"],
        rate_limit=20,
        timeout_seconds=60,
        requires_api_key=True,
        input_schema=ToolSchema(
            type="object",
            properties={
                "query": {
                    "type": "string",
                    "description": "Search query to send to Perplexity",
                },
                "focus": {
                    "type": "string",
                    "description": "Search focus area",
                    "enum": [
                        "internet",
                        "academic",
                        "writing",
                        "wolfram",
                        "youtube",
                        "reddit",
                    ],
                },
            },
            required=["query"],
        ),
    )
    registry.register(perplexity_meta, PerplexityTool())

    # HTTP Request
    http_meta = ToolMetadata(
        id="http_request",
        name="HTTP Request",
        description="Make HTTP requests to external APIs",
        tool_type=ToolType.HTTP,
        allowed_roles=["researcher"],
        rate_limit=100,
        timeout_seconds=30,
        input_schema=ToolSchema(
            type="object",
            properties={
                "url": {
                    "type": "string",
                    "description": "URL to request",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers",
                },
                "body": {
                    "type": "object",
                    "description": "Request body (for POST/PUT/PATCH)",
                },
            },
            required=["url"],
        ),
    )
    registry.register(http_meta, HTTPTool())

    # Mock Search (for testing without API keys)
    mock_meta = ToolMetadata(
        id="mock_search",
        name="Mock Search",
        description="Mock search tool for testing",
        tool_type=ToolType.MOCK,
        allowed_roles=["researcher", "planner"],
        rate_limit=1000,
        timeout_seconds=5,
        input_schema=ToolSchema(
            type="object",
            properties={
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            required=["query"],
        ),
    )
    registry.register(mock_meta, MockSearchTool())

    # Calculator (commonly needed)
    calc_meta = ToolMetadata(
        id="calculate",
        name="Calculator",
        description="Perform mathematical calculations",
        tool_type=ToolType.MOCK,
        allowed_roles=["researcher", "planner"],
        rate_limit=1000,
        timeout_seconds=5,
        input_schema=ToolSchema(
            type="object",
            properties={
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                },
            },
            required=["expression"],
        ),
    )

    # Simple calculator executor
    def calculate_executor(expression: str) -> dict:
        try:
            # Safe eval for simple math
            allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}

    registry.register(calc_meta, calculate_executor)

    logger.info(f"Initialized {len(registry.list_all())} default tools")


async def ask_l(query: str) -> dict:
    """
    Trigger reactive task generation and execution pipeline.

    This tool allows external systems to trigger L's reactive task dispatch
    by providing a user query that gets converted to tasks and executed.

    Args:
        query: User query text

    Returns:
        Dictionary with execution results: task_ids, status, message
    """
    import structlog
    from core.agents.executor import _generate_tasks_from_query
    from runtime.task_queue import dispatch_task_immediate, QueuedTask
    from uuid import uuid4

    logger = structlog.get_logger(__name__)

    if not query or not query.strip():
        return {
            "success": False,
            "error": "query is required",
            "task_ids": [],
        }

    try:
        # Generate tasks from query
        task_specs = await _generate_tasks_from_query(query)

        if not task_specs:
            return {
                "success": False,
                "error": "No tasks generated from query",
                "task_ids": [],
            }

        task_ids = []

        # Dispatch each task immediately
        for spec in task_specs:
            try:
                task = QueuedTask(
                    task_id=str(uuid4()),
                    name=spec["name"],
                    payload=spec["payload"],
                    handler=spec["handler"],
                    agent_id="L",
                    priority=spec.get("priority", 5),
                    tags=["ask_l", "reactive"],
                )

                task_id = await dispatch_task_immediate(task)
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"Failed to dispatch task from ask_l: {e}", exc_info=True)

        return {
            "success": True,
            "task_ids": task_ids,
            "message": f"Dispatched {len(task_ids)} task(s) from query",
        }

    except Exception as e:
        logger.error(f"ask_l failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "task_ids": [],
        }


async def get_l_memory_state() -> dict:
    """
    Expose L's current memory context.

    Retrieves L's memory state from substrate including governance rules,
    project history, and recent task context.

    Returns:
        Dictionary with memory state: governance_rules, project_history, recent_tasks
    """
    import structlog
    from memory.substrate_service import get_service

    logger = structlog.get_logger(__name__)

    try:
        substrate = await get_service()
        if not substrate:
            return {
                "success": False,
                "error": "Memory substrate not available",
            }

        memory_state = {}

        # Search for recent governance and project history packets
        governance_packets = await substrate.search_packets_by_type(
            packet_type="governance_meta",
            agent_id="L",
            limit=10,
        )
        if governance_packets:
            memory_state["governance_rules"] = [
                p.get("payload", {}) for p in governance_packets
            ]

        project_packets = await substrate.search_packets_by_type(
            packet_type="project_history",
            agent_id="L",
            limit=10,
        )
        if project_packets:
            memory_state["project_history"] = [
                p.get("payload", {}) for p in project_packets
            ]

        # Get recent task execution results
        task_packets = await substrate.search_packets_by_type(
            packet_type="task_execution_result",
            agent_id="L",
            limit=10,
        )
        if task_packets:
            memory_state["recent_tasks"] = [p.get("payload", {}) for p in task_packets]

        return {
            "success": True,
            "memory_state": memory_state,
            "summary": {
                "governance_rules": len(memory_state.get("governance_rules", [])),
                "project_history": len(memory_state.get("project_history", [])),
                "recent_tasks": len(memory_state.get("recent_tasks", [])),
            },
        }

    except Exception as e:
        logger.error(f"get_l_memory_state failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def recall_task_history(num_tasks: int = 10) -> List[dict]:
    """
    Retrieve recent task execution history.

    Queries memory substrate for recent task execution results.

    Args:
        num_tasks: Number of recent tasks to retrieve (default: 10)

    Returns:
        List of task result dicts with task_id, status, duration_ms, error, etc.
    """
    import structlog
    from memory.substrate_service import get_service

    logger = structlog.get_logger(__name__)

    try:
        substrate = await get_service()
        if not substrate:
            logger.warning(
                "Memory substrate not available - cannot recall task history"
            )
            return []

        # Search for task execution result packets
        packets = await substrate.search_packets_by_type(
            packet_type="task_execution_result",
            agent_id="L",
            limit=num_tasks,
        )

        # Extract task results from packets
        task_history = []
        for packet in packets:
            payload = packet.get("payload", {})
            if payload:
                task_history.append(
                    {
                        "task_id": payload.get("task_id"),
                        "status": payload.get("status"),
                        "iterations": payload.get("iterations", 0),
                        "duration_ms": payload.get("duration_ms", 0),
                        "error": payload.get("error"),
                        "completed_at": payload.get("completed_at"),
                    }
                )

        logger.info(f"Recalled {len(task_history)} task(s) from history")
        return task_history

    except Exception as e:
        logger.error(f"recall_task_history failed: {e}", exc_info=True)
        return []


# =============================================================================
# Tool Router Find (GMP-78: Semantic Tool Retrieval)
# =============================================================================


async def tool_router_find(
    query: str,
    top_k: int = 5,
    exclude_categories: list[str] | None = None,
) -> dict:
    """
    Find relevant tools for a task using semantic search.

    GMP-78: Semantic Tool Retrieval executor function.

    Uses pgvector embeddings to find the most relevant tools for a given query.
    This allows agents to discover which tools are appropriate for their task
    without having all 100+ tools in context.

    Args:
        query: Task description or user query
        top_k: Maximum number of tools to return (default 5)
        exclude_categories: Tool categories to exclude (e.g., ["governance"])

    Returns:
        Dict with:
        - success: bool
        - tools: List of tool info dicts (name, description, category, similarity)
        - query: The original query
        - count: Number of tools found
    """
    import structlog

    logger = structlog.get_logger(__name__)

    if not query or not query.strip():
        return {
            "success": False,
            "error": "query is required",
            "tools": [],
            "count": 0,
        }

    try:
        from core.tools.tool_embeddings import find_relevant_tools

        results = await find_relevant_tools(
            query=query,
            top_k=top_k,
            exclude_categories=exclude_categories,
        )

        tools = [
            {
                "name": r.tool_name,
                "description": r.description,
                "category": r.category,
                "similarity": round(r.similarity, 3),
                "negative_constraints": r.negative_constraints,
            }
            for r in results
        ]

        logger.info(
            f"tool_router_find: found {len(tools)} tools for query",
            query=query[:50],
            top_k=top_k,
        )

        return {
            "success": True,
            "tools": tools,
            "query": query,
            "count": len(tools),
        }

    except ImportError as e:
        logger.warning(f"tool_embeddings not available: {e}")
        return {
            "success": False,
            "error": "Tool embeddings service not available",
            "tools": [],
            "count": 0,
        }
    except Exception as e:
        logger.error(f"tool_router_find failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "tools": [],
            "count": 0,
        }
