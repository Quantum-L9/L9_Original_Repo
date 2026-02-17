"""
L9 Core Tools - Base Registry
Version: 2.1.0

Universal in-memory tool registry for ALL L9 tools (research + L-CTO + custom).
NO database persistence - tools are registered at startup.

Architecture:
- This is the BASE STORAGE layer (singleton via get_tool_registry())
- ExecutorToolRegistry in registry_adapter.py WRAPS this for governance + OpenAI format
- L tools are registered via sync_runtime_tools_to_primary() bridge at server startup
- Research tools (Perplexity, HTTP, Mock) auto-registered on first access

Production-ready features (v2.1.0):
- Time-based sliding window rate limiting
- Tool schema support for OpenAI function calling
- Async execution with timeout handling
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Base Registry",
    "module_version": "2.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "base_registry",
    "type": "enum",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "Perplexity API", "PostgreSQL"],
        "memory_layers": ["episodic_memory", "semantic_memory", "working_memory"],
        "imported_by": [
            "core.agents.bootstrap.phase_0_validate",
            "core.singleton_registry",
            "core.tools.registry_adapter",
            "runtime.l_tools",
            "services.research.tools.__init__",
            "services.research.tools.tool_resolver",
            "tests.integration.test_l_bootstrap",
            "tests.integration.test_research_tool_integration",
            "tests.test_tool_registry",
            "tests.unit.test_registry_adapter_sanitization",
        ],
    },
}
# ============================================================================

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from core.singleton_auto_registry import register_singleton
from runtime.tool_registry import register_tool

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
        """
        Represents metadata for a registered tool in the L9 core tools registry, including capabilities, access control, and rate limits.

        Args:
            id: Unique identifier for the tool, ensuring canonical recognition.
            name: Human-readable name of the tool.

        Returns:
            An instance of ToolMetadata containing the tool's descriptive and operational details.
        """

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
    """
    Config class for managing registry settings in L9 Core Tools.
    Args:
        use_enum_values: If True, enums are represented by their values in configurations.
    """
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    requires_api_key: bool = Field(
        default=False, description="Whether tool requires API key"
    )
    input_schema: ToolSchema | None = Field(
        default=None, description="JSON Schema for tool parameters"
    )

    class Config:
        """
        Config class for L9 Core Tools registry configuration, managing registry behavior.

        Args:
            use_enum_values: Boolean indicating if enum values should be used instead of enum instances.

        No return value.
        """

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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self._window_seconds)
        current = len([t for t in self._calls[key] if t > cutoff])
        return max(0, limit - current)

    def reset(self, key: str | None = None) -> None:
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
        executor: Any | None = None,
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

    def get(self, tool_id: str) -> ToolMetadata | None:
        """Get tool metadata by ID."""
        return self._tools.get(tool_id)

    def get_executor(self, tool_id: str) -> Any | None:
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

    def reset_rate_limits(self, tool_id: str | None = None) -> None:
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

    @must_stay_async("callers use await")
    async def execute_tool(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        principal_id: str,
    ) -> dict[str, Any]:
        """
        Execute a tool with timeout handling.

        Args:
            tool_id: Tool to execute
            arguments: Arguments for tool
            principal_id: REQUIRED - Principal identifier

        Returns:
            Dict with success, result/error, duration_ms
        """
        if not principal_id or not principal_id.strip():
            raise RuntimeError(
                f"principal_id REQUIRED for tool execution: {tool_id}"
            )

        start_time = datetime.now(UTC)

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

            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            logger.info(f"Tool {tool_id} completed in {duration_ms}ms")

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
            }

        except TimeoutError:
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.warning(f"Tool {tool_id} timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Tool execution timed out after {timeout}s",
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.exception(f"Tool {tool_id} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
            }


# Singleton instance
_registry: ToolRegistry | None = None


@register_singleton(
    name="tool_registry",
    lifecycle="startup",
    description="In-memory registry of available tools with rate limiting",
)
def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _initialize_default_tools(_registry)
    return _registry


def _initialize_default_tools(registry: ToolRegistry) -> None:
    """Initialize default tools in registry with schemas.

    NOTE: perplexity_search and http_request are registered dynamically
    via sync_runtime_tools_to_primary() bridge at startup (ADR-0094).
    Only testing/utility tools that have no dynamic registration path
    remain here.
    """
    from services.research.tools.tool_wrappers import (
        MockSearchTool,
    )

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
                    """
                    Calculates the result of a safe literal expression evaluation within the L9 Core Tools registry.

                    Args:
                        expression: str representing the literal expression to evaluate.

                    Returns:
                        dict containing the original expression and its evaluated result.

                    Raises:
                        ValueError: if the expression cannot be safely evaluated.
                    """
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                },
            },
            required=["expression"],
        ),
    )

    # Simple calculator executor
    def calculate_executor(expression: str) -> dict:
        """
        Calculates the result of a safe literal expression evaluation within the L9 Core Tools registry.

        Args:
            expression: str representing a literal expression to evaluate.

        Returns:
            dict containing the original expression and its evaluated result.

        Raises:
            ValueError: if the expression cannot be safely evaluated.
        """
        try:
            # Safe evaluation using ast.literal_eval (only allows literals)
            import ast

            result = ast.literal_eval(expression)
            return {"result": result, "expression": expression}
        except (ValueError, SyntaxError) as e:
            return {"error": f"Invalid expression: {e!s}", "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}

    registry.register(calc_meta, calculate_executor)

    logger.info(f"Initialized {len(registry.list_all())} default tools")


async def recall_task_history(num_tasks: int = 10) -> list[dict]:
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


@register_tool(category="routing", priority=10, description="tool_router_find tool")
@must_stay_async("callers use await")
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


# =============================================================================
# Saga Tools (GMP-88: Cross-DB Chain Operations)
# =============================================================================


@register_tool(category="saga", priority=10, description="saga_fetch_and_enrich tool")
@must_stay_async("callers use await")
async def saga_fetch_and_enrich(
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 10,
) -> dict:
    """
    Cross-DB saga: vector search → entity extraction → graph enrichment.

    GMP-88: Saga Tool Implementation

    Steps:
    1. Postgres: Vector similarity search on query (memory_search)
    2. Extract: Identify entity IDs from results
    3. Neo4j: Enrich entities with graph relationships
    4. Combine: Merge structured data + graph context

    Args:
        query: Search query for vector similarity
        entity_types: Optional filter for entity types to extract
        limit: Maximum entities to process

    Returns:
        Dict with combined results from both databases
    """
    import structlog

    logger = structlog.get_logger(__name__)

    if not query or not query.strip():
        return {
            "success": False,
            "error": "query is required",
            "results": [],
        }

    results: dict[str, object] = {
        "success": True,
        "query": query,
        "postgres_results": [],
        "neo4j_enrichment": [],
        "combined": [],
    }

    try:
        # Step 1: Vector search in Postgres
        try:
            from memory.substrate_service import get_service

            substrate = await get_service()
            if substrate:
                search_results = await substrate.search_semantic(
                    query=query,
                    limit=limit,
                    entity_types=entity_types,
                )
                postgres_results: list[object] = search_results or []
                results["postgres_results"] = postgres_results
                logger.info(
                    f"saga_fetch_and_enrich: Postgres found {len(postgres_results)} results"
                )
        except Exception as e:
            logger.warning(f"Postgres search failed in saga: {e}")
            results["postgres_results"] = []

        # Step 2: Extract entity IDs
        entity_ids = []
        pg_results = results.get("postgres_results", [])
        for item in pg_results if isinstance(pg_results, list) else []:
            if isinstance(item, dict):
                eid = item.get("entity_id") or item.get("id") or item.get("source_id")
                if eid:
                    entity_ids.append(str(eid))

        entity_ids = list(set(entity_ids))[:limit]  # Dedupe and limit

        # Step 3: Neo4j enrichment
        if entity_ids:
            try:
                from memory.substrate_dag import SubstrateDAG

                dag = SubstrateDAG()
                enrichment = []
                _get_related = getattr(dag, "get_related_entities", None)
                for eid in entity_ids[:5]:  # Limit graph queries
                    try:
                        related = await _get_related(
                            entity_id=eid,
                            relationship_types=None,
                            depth=1,
                        ) if _get_related else None
                        if related:
                            enrichment.append(
                                {
                                    "entity_id": eid,
                                    "relationships": related,
                                }
                            )
                    except Exception as inner_e:
                        logger.debug(f"Could not enrich entity {eid}: {inner_e}")

                results["neo4j_enrichment"] = enrichment
                logger.info(
                    f"saga_fetch_and_enrich: Neo4j enriched {len(enrichment)} entities"
                )
            except Exception as e:
                logger.warning(f"Neo4j enrichment failed in saga: {e}")
                results["neo4j_enrichment"] = []

        # Step 4: Combine results
        neo4j_enrich = results.get("neo4j_enrichment", [])
        enrichment_map = {
            e["entity_id"]: e["relationships"] for e in (neo4j_enrich if isinstance(neo4j_enrich, list) else [])
        }
        combined = []
        pg_results2 = results.get("postgres_results", [])
        for item in pg_results2 if isinstance(pg_results2, list) else []:
            eid = item.get("entity_id") or item.get("id") or item.get("source_id")
            combined_item = {
                "data": item,
                "relationships": enrichment_map.get(str(eid), []) if eid else [],
            }
            combined.append(combined_item)

        results["combined"] = combined
        results["entity_count"] = len(entity_ids)

        return results

    except Exception as e:
        logger.error(f"saga_fetch_and_enrich failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


@register_tool(category="saga", priority=10, description="saga_enrich_entities tool")
@must_stay_async("callers use await")
async def saga_enrich_entities(
    entity_ids: list[str],
    relationship_types: list[str] | None = None,
    depth: int = 1,
) -> dict:
    """
    Cross-DB saga: lookup entities → enrich with graph relationships.

    GMP-88: Saga Tool Implementation

    Steps:
    1. Take entity IDs (from previous step or user input)
    2. Neo4j: Query relationships up to specified depth
    3. Return enriched entity graph

    Args:
        entity_ids: List of entity IDs to enrich
        relationship_types: Optional filter for relationship types
        depth: Traversal depth (default 1, max 3)

    Returns:
        Dict with enriched entity data including relationships
    """
    import structlog

    logger = structlog.get_logger(__name__)

    if not entity_ids:
        return {
            "success": False,
            "error": "entity_ids is required",
            "entities": [],
        }

    # Cap depth at 3 to prevent expensive queries
    depth = min(max(1, depth), 3)

    results = {
        "success": True,
        "entity_ids": entity_ids,
        "depth": depth,
        "entities": [],
    }

    try:
        from memory.substrate_dag import SubstrateDAG

        dag = SubstrateDAG()
        entities = []
        _get_related = getattr(dag, "get_related_entities", None)

        for eid in entity_ids[:20]:  # Limit to 20 entities
            try:
                # Get entity relationships
                related = await _get_related(
                    entity_id=str(eid),
                    relationship_types=relationship_types,
                    depth=depth,
                ) if _get_related else None

                entities.append(
                    {
                        "entity_id": str(eid),
                        "relationships": related or [],
                        "relationship_count": len(related) if related else 0,
                    }
                )
            except Exception as e:
                logger.debug(f"Could not enrich entity {eid}: {e}")
                entities.append(
                    {
                        "entity_id": str(eid),
                        "relationships": [],
                        "error": str(e),
                    }
                )

        results["entities"] = entities
        results["enriched_count"] = sum(1 for e in entities if e.get("relationships"))

        logger.info(
            f"saga_enrich_entities: enriched {results['enriched_count']}/{len(entity_ids)} entities"
        )

        return results

    except ImportError as e:
        logger.warning(f"SubstrateDAG not available: {e}")
        return {
            "success": False,
            "error": "Graph database service not available",
            "entities": [],
        }
    except Exception as e:
        logger.error(f"saga_enrich_entities failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "entities": [],
        }


@register_tool(
    category="saga", priority=10, description="saga_timeline_correlation tool"
)
@must_stay_async("callers use await")
async def saga_timeline_correlation(
    start_entity_id: str,
    time_range_hours: int = 24,
    event_types: list[str] | None = None,
) -> dict:
    """
    Cross-DB saga: fetch events → trace causal chains → correlate timeline.

    GMP-88: Saga Tool Implementation

    Steps:
    1. Postgres: Fetch events for entity in time range
    2. Neo4j: Trace causal chains between events
    3. Return correlated timeline with causality links

    Args:
        start_entity_id: Entity to trace timeline for
        time_range_hours: Hours to look back (default 24)
        event_types: Optional filter for event types

    Returns:
        Dict with timeline events and causal relationships
    """
    from datetime import datetime, timezone, timedelta

    import structlog

    logger = structlog.get_logger(__name__)

    if not start_entity_id:
        return {
            "success": False,
            "error": "start_entity_id is required",
            "timeline": [],
        }

    # Cap time range at 168 hours (1 week)
    time_range_hours = min(max(1, time_range_hours), 168)

    results: dict[str, object] = {
        "success": True,
        "entity_id": start_entity_id,
        "time_range_hours": time_range_hours,
        "timeline": [],
        "causal_chains": [],
    }

    try:
        # Step 1: Fetch events from Postgres
        events = []
        try:
            from memory.substrate_service import get_service

            substrate = await get_service()
            if substrate:
                datetime.now(UTC) - timedelta(hours=time_range_hours)

                # Search for events related to entity
                search_results = await substrate.search_packets_by_type(
                    packet_type=event_types[0] if event_types else "event",
                    agent_id=None,  # All agents
                    limit=50,
                )

                # Filter by entity and time
                for packet in search_results or []:
                    payload = packet.get("payload", {})
                    if payload.get("entity_id") == start_entity_id:
                        events.append(
                            {
                                "event_id": packet.get("id"),
                                "type": packet.get("kind"),
                                "timestamp": packet.get("created_at"),
                                "payload": payload,
                            }
                        )

                events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                events = events[:30]  # Limit to 30 events

        except Exception as e:
            logger.warning(f"Event fetch failed in saga: {e}")

        results["timeline"] = events

        # Step 2: Trace causal chains in Neo4j
        if events:
            try:
                from memory.substrate_dag import SubstrateDAG

                dag = SubstrateDAG()
                causal_chains = []
                _get_related = getattr(dag, "get_related_entities", None)

                event_ids = [e.get("event_id") for e in events if e.get("event_id")]

                # Find causal relationships between events
                for event_id in event_ids[:10]:  # Limit graph queries
                    try:
                        related = await _get_related(
                            entity_id=str(event_id),
                            relationship_types=["CAUSED_BY", "TRIGGERED", "FOLLOWS"],
                            depth=2,
                        ) if _get_related else None
                        if related:
                            causal_chains.append(
                                {
                                    "event_id": event_id,
                                    "causal_links": related,
                                }
                            )
                    except Exception:
                        logger.debug(
                            "base_registry.causal_link_trace_failed", event_id=event_id
                        )

                results["causal_chains"] = causal_chains

            except Exception as e:
                logger.warning(f"Causal chain trace failed: {e}")

        results["event_count"] = len(events)
        causal_list = results.get("causal_chains", [])
        results["causal_chain_count"] = len(causal_list) if isinstance(causal_list, list) else 0

        logger.info(
            f"saga_timeline_correlation: found {results['event_count']} events, "
            f"{results['causal_chain_count']} causal chains"
        )

        return results

    except Exception as e:
        logger.error(f"saga_timeline_correlation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timeline": [],
        }


@register_tool(category="saga", priority=10, description="saga_execute_custom tool")
@must_stay_async("callers use await")
async def saga_execute_custom(
    steps: list[dict],
) -> dict:
    """
    Execute a custom saga with user-defined steps.

    GMP-88: Saga Tool Implementation

    Each step must have:
    - tool: str (tool name to call)
    - args: dict (arguments for tool)
    - output_key: str (key to store result)

    Results are passed forward: step N can reference step N-1's output
    using {{prev.key}} syntax in args.

    Args:
        steps: List of step definitions

    Returns:
        Dict with results from each step
    """
    import re

    import structlog

    logger = structlog.get_logger(__name__)

    if not steps:
        return {
            "success": False,
            "error": "steps is required",
            "results": {},
        }

    # Validate step structure
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return {
                "success": False,
                "error": f"Step {i} must be a dict",
                "results": {},
            }
        if "tool" not in step:
            return {
                "success": False,
                "error": f"Step {i} missing 'tool' field",
                "results": {},
            }

    # Limit to 5 steps for safety
    if len(steps) > 5:
        return {
            "success": False,
            "error": "Maximum 5 steps allowed in custom saga",
            "results": {},
        }

    # Available saga tools (safe list)
    ALLOWED_TOOLS = {
        "saga_fetch_and_enrich": saga_fetch_and_enrich,
        "saga_enrich_entities": saga_enrich_entities,
        "saga_timeline_correlation": saga_timeline_correlation,
        "tool_router_find": tool_router_find,
    }

    results = {
        "success": True,
        "steps_executed": 0,
        "results": {},
    }

    prev_result = {}

    try:
        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            args = step.get("args", {})
            output_key = step.get("output_key", f"step_{i}")

            # Check tool is allowed
            if tool_name not in ALLOWED_TOOLS:
                results["results"][output_key] = {
                    "success": False,
                    "error": f"Tool '{tool_name}' not allowed in custom saga",
                }
                continue

            # Substitute {{prev.X}} references
            for arg_key, arg_val in args.items():
                if isinstance(arg_val, str) and "{{prev." in arg_val:
                    # Extract key from {{prev.key}}
                    match = re.search(r"\{\{prev\.(\w+)\}\}", arg_val)
                    if match:
                        ref_key = match.group(1)
                        if ref_key in prev_result:
                            args[arg_key] = prev_result[ref_key]

            # Execute tool
            tool_func = ALLOWED_TOOLS[tool_name]
            try:
                step_result = await tool_func(**args)
                results["results"][output_key] = step_result
                results["steps_executed"] += 1

                # Store for next step reference
                if isinstance(step_result, dict):
                    prev_result = step_result

            except Exception as e:
                logger.warning(f"Custom saga step {i} failed: {e}")
                results["results"][output_key] = {
                    "success": False,
                    "error": str(e),
                }

        logger.info(
            f"saga_execute_custom: executed {results['steps_executed']}/{len(steps)} steps"
        )

        return results

    except Exception as e:
        logger.error(f"saga_execute_custom failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": {},
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-019",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.executor",
        "core.tools.tool_embeddings",
        "memory.substrate_dag",
        "memory.substrate_service",
        "runtime.task_queue",
    ],
    "tags": [
        "api",
        "async",
        "data-models",
        "debugging",
        "enum",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "pydantic",
    ],
    "keywords": [
        "all",
        "ask",
        "calculate",
        "check",
        "correlation",
        "custom",
        "disable",
        "enable",
    ],
    "business_value": "Provides base registry components including ToolType, ToolSchema, ToolMetadata",
    "last_modified": "2026-01-17T23:47:56Z",
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
