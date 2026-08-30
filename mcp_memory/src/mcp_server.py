"""
MCP (Model Context Protocol) Server Implementation.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Mcp Server",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "data_models",
    "module_name": "mcp_server",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from datetime import UTC
from typing import Any

import structlog
from pydantic import BaseModel, ValidationError

from core.config_constants import (
    DEFAULT_SEARCH_SCOPES,
    MCP_SEARCH_SCOPES,
    MCP_WRITE_SCOPES,
    get_allowed_scopes_for_caller,
    get_default_project_id,
)
from core.decorators import must_stay_async
from src.config import settings

logger = structlog.get_logger(__name__)


class MCPTool(BaseModel):
    """
    Provides a representation of MCP (Model Context Protocol) tools and their invocation details within the MCP server framework.

    Args:
        name: The name identifier of the MCP tool.
        description: A brief description of the MCP tool's purpose.
        inputSchema: A dictionary defining the expected input structure for the tool.

    Args:
        name: The name of the MCP tool call to execute.
        arguments: A dictionary of arguments to pass to the MCP tool.

    Returns:
        A list of MCPTool instances representing available MCP tools.
    """

    name: str
    description: str
    inputSchema: dict[str, Any]


class MCPToolCall(BaseModel):
    """
    Represents a call to a specific tool within the MCP (Model Context Protocol) server, encapsulating tool name and arguments.

    Args:
        name: The identifier of the MCP tool to invoke.
        arguments: A dictionary of parameters to pass to the tool.

    Returns:
        An instance of MCPToolCall with specified tool name and arguments.
    """

    name: str
    arguments: dict[str, Any]


def get_mcp_tools() -> list[MCPTool]:
    """Returns a list of MCPTool instances representing available MCP tools for model context management."""
    return [
        MCPTool(
            name="save_memory",
            description="Save a memory to the database with automatic embedding",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content"},
                    "kind": {
                        "type": "string",
                        "enum": ["preference", "fact", "context", "error", "success"],
                    },
                    "scope": {
                        "type": "string",
                        "enum": MCP_WRITE_SCOPES,  # ADR-0098
                    },
                    "duration": {"type": "string", "enum": ["short", "medium", "long"]},
                    "user_id": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "kernel:identity",
                                "kernel:cognitive",
                                "kernel:behavioral",
                                "kernel:execution",
                                "kernel:safety",
                                "agent:l-cto",
                                "agent:codegen",
                                "memory:substrate",
                                "memory:packet",
                                "orchestration:routing",
                                "orchestration:planning",
                                "tool:registry",
                                "tool:approval",
                                "api:routes",
                                "api:webhook",
                                "infra:docker",
                                "infra:vps",
                                "infra:database",
                                "gmp:phase",
                                "gmp:audit",
                                "debug:error",
                                "debug:fix",
                                "igor:preference",
                                "igor:context",
                            ],
                        },
                        "description": "L9 hierarchical memory categories (domain:specificity)",
                    },
                    "importance": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["content", "kind", "duration", "user_id"],
            },
        ),
        MCPTool(
            name="search_memory",
            description="Search memories using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string"},
                    "scopes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": MCP_SEARCH_SCOPES,  # ADR-0098
                        },
                    },
                    "kinds": {"type": "array", "items": {"type": "string"}},
                    "top_k": {"type": "integer", "default": 5},
                    "threshold": {"type": "number", "default": 0.7},
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long", "all"],
                    },
                },
                "required": ["query", "user_id"],
            },
        ),
        MCPTool(
            name="get_memory_stats",
            description="Get statistics about stored memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "duration": {
                        "type": "string",
                        "enum": ["short", "medium", "long", "all"],
                    },
                },
                "required": [],
            },
        ),
        MCPTool(
            name="delete_expired_memories",
            description="Cleanup expired memories",
            inputSchema={
                "type": "object",
                "properties": {"dry_run": {"type": "boolean", "default": True}},
                "required": [],
            },
        ),
        MCPTool(
            name="compound_memories",
            description="Merge highly similar memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "threshold": {"type": "number", "default": 0.92},
                },
                "required": ["user_id"],
            },
        ),
        MCPTool(
            name="apply_decay",
            description="Apply importance decay to unused memories",
            inputSchema={
                "type": "object",
                "properties": {"dry_run": {"type": "boolean", "default": True}},
                "required": [],
            },
        ),
        # =============================================================================
        # 10x Memory Upgrade Tools
        # =============================================================================
        MCPTool(
            name="get_context",
            description="Auto-retrieve relevant memories for context injection before a task. Returns top memories matching the task description plus recent context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "What you're about to work on - memories matching this will be retrieved",
                    },
                    "user_id": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "include_recent": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include memories from last 24h session context",
                    },
                    "kinds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by memory kinds (preference, fact, context, error, success)",
                    },
                },
                "required": ["task_description", "user_id"],
            },
        ),
        MCPTool(
            name="extract_session_learnings",
            description="Extract and store learnings from a completed session. Call at session end to capture what was learned.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "session_id": {"type": "string"},
                    "session_summary": {
                        "type": "string",
                        "description": "Brief summary of what happened this session",
                    },
                    "key_decisions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key decisions made during session",
                    },
                    "errors_encountered": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Errors that occurred and how they were fixed",
                    },
                    "successes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What worked well this session",
                    },
                },
                "required": ["user_id", "session_id", "session_summary"],
            },
        ),
        MCPTool(
            name="get_proactive_suggestions",
            description="Get proactive memory suggestions based on current context. Surfaces relevant past experiences, error fixes, and preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_context": {
                        "type": "string",
                        "description": "What you're currently working on",
                    },
                    "user_id": {"type": "string"},
                    "include_error_fixes": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include past error/fix pairs that might be relevant",
                    },
                    "include_preferences": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include user preferences relevant to this context",
                    },
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["current_context", "user_id"],
            },
        ),
        MCPTool(
            name="query_temporal",
            description="Query memory changes over time. Answer 'what changed since X' or 'show timeline of Y'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "since": {
                        "type": "string",
                        "description": "ISO datetime - get changes since this time",
                    },
                    "until": {
                        "type": "string",
                        "description": "ISO datetime - get changes until this time",
                    },
                    "kinds": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by memory kinds",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["changes", "timeline", "diff"],
                        "default": "changes",
                        "description": "Type of temporal query",
                    },
                },
                "required": ["user_id"],
            },
        ),
        MCPTool(
            name="save_memory_with_confidence",
            description="Save a memory with explicit confidence scoring and relationship linking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content"},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "preference",
                            "fact",
                            "context",
                            "error",
                            "success",
                            "learning",
                            "decision",
                        ],
                    },
                    "scope": {
                        "type": "string",
                        "enum": MCP_WRITE_SCOPES,  # ADR-0098
                    },
                    "duration": {"type": "string", "enum": ["short", "medium", "long"]},
                    "user_id": {"type": "string"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 1.0,
                        "description": "How confident are we in this memory (0-1)",
                    },
                    "source": {
                        "type": "string",
                        "default": "cursor",
                        "description": "Source of this memory (cursor, user, inferred)",
                    },
                    "related_memory_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "IDs of related memories to link",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "importance": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["content", "kind", "duration", "user_id"],
            },
        ),
        # =============================================================================
        # Graph (Neo4j) Tools
        # =============================================================================
        MCPTool(
            name="graph_query",
            description="Run a Cypher query on Neo4j graph database. Use for relationship traversal and graph analytics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cypher query string (e.g., 'MATCH (n:Agent) RETURN n LIMIT 10')",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters for parameterized queries",
                    },
                },
                "required": ["query"],
            },
        ),
        MCPTool(
            name="graph_get_entity",
            description="Get an entity node from the graph by type and ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Node label (Agent, Session, Memory, Task, etc.)",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity identifier",
                    },
                },
                "required": ["entity_type", "entity_id"],
            },
        ),
        MCPTool(
            name="graph_get_context",
            description="Get graph context for a domain (memory, agents, tools, etc.). Returns entities and relationships.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to query (memory, agents, tools, orchestration, etc.)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum results to return",
                    },
                },
                "required": ["domain"],
            },
        ),
        # =============================================================================
        # Graph Event (Neo4j Event nodes) Tools
        # =============================================================================
        MCPTool(
            name="graph_create_event",
            description="Create an Event node in Neo4j timeline. Use for logging actions, agent responses, and building causality chains.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Unique event identifier (e.g., UUID)",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type (e.g., 'user_action', 'agent_response', 'tool_call')",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO timestamp (e.g., '2026-01-28T12:00:00Z')",
                    },
                    "properties": {
                        "type": "object",
                        "description": "Additional event properties (content, metadata, etc.)",
                    },
                    "parent_event_id": {
                        "type": "string",
                        "description": "Optional parent event ID for causality chain (creates TRIGGERED relationship)",
                    },
                },
                "required": ["event_id", "event_type", "timestamp"],
            },
        ),
        MCPTool(
            name="graph_get_event_timeline",
            description="Get Event nodes from Neo4j in a time range. Use for reviewing history and temporal analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "ISO timestamp start (optional)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "ISO timestamp end (optional)",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Filter by event type (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum events to return",
                    },
                },
                "required": [],
            },
        ),
        MCPTool(
            name="graph_get_temporal_events",
            description="Get Event nodes related to a specific entity within a time range. Use for entity-centric timeline queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity ID to get events for",
                    },
                    "start": {
                        "type": "string",
                        "description": "ISO timestamp start (optional)",
                    },
                    "end": {
                        "type": "string",
                        "description": "ISO timestamp end (optional)",
                    },
                },
                "required": ["entity"],
            },
        ),
        MCPTool(
            name="graph_get_event_sequence",
            description="Get ordered sequence of Event nodes for an entity. Use for tracing causality and understanding event flow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity ID to get event sequence for",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum events to return",
                    },
                },
                "required": ["entity"],
            },
        ),
        # =============================================================================
        # Cache (Redis) Tools
        # =============================================================================
        MCPTool(
            name="cache_get",
            description="Get a value from Redis cache by key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Cache key to retrieve",
                    },
                },
                "required": ["key"],
            },
        ),
        MCPTool(
            name="cache_set",
            description="Set a value in Redis cache with optional TTL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Cache key",
                    },
                    "value": {
                        "type": ["string", "object", "array", "number", "boolean"],
                        "description": "Value to store (will be JSON serialized if not string)",
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time-to-live in seconds (optional)",
                    },
                },
                "required": ["key", "value"],
            },
        ),
        MCPTool(
            name="cache_get_session_context",
            description="Get session context from Redis cache for this agent (Cursor, L, etc.). Returns fast-access session state. Key is namespaced by caller so each agent has its own context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (defaults to daily session UUID if not provided)",
                    },
                },
                "required": [],
            },
        ),
        MCPTool(
            name="cache_set_session_context",
            description="Store session context in Redis cache for this agent (any L9 agent: Cursor, L, Mac, etc.). Use at session end or milestones so the agent can resume without amnesia. Key is namespaced by caller.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (defaults to daily session if not provided)",
                    },
                    "context": {
                        "type": "object",
                        "description": "Context dict: summary, files_touched, current_task, decisions, next_steps",
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time-to-live in seconds (default 86400 = 24h)",
                    },
                },
                "required": ["context"],
            },
        ),
        MCPTool(
            name="cache_delete",
            description="Delete a key from Redis cache.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Cache key to delete",
                    },
                },
                "required": ["key"],
            },
        ),
        MCPTool(
            name="cache_keys",
            description="Get all keys matching a pattern from Redis cache.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Redis key pattern (e.g., 'l9:tool_cache:*')",
                    },
                },
                "required": ["pattern"],
            },
        ),
    ]


@must_stay_async("callers use await")
async def handle_tool_call(
    tool: MCPToolCall,
    user_id: str,
    caller: Any = None,
    substrate_service: Any = None,  # Optional: MemorySubstrateService for main pipeline
) -> dict[str, Any]:
    """Handle MCP tool call with caller-enforced governance.

    Args:
        tool: The tool call request
        user_id: Shared user_id (L_CTO_USER_ID)
        caller: CallerIdentity with caller_id, creator, source (L or C)

    See: mcp_memory/memory-setup-instructions.md for governance spec.

    Raises:
        ValidationError: If tool arguments don't match expected schema
        ValueError: If governance rules are violated (e.g., Cursor writing l-private)
    """
    import json
    import time

    from src.db import execute
    from src.models import (  # Graph (Neo4j) tool args; Cache (Redis) tool args
        ApplyDecayArgs,
        CacheDeleteArgs,
        CacheGetArgs,
        CacheGetSessionContextArgs,
        CacheKeysArgs,
        CacheSetArgs,
        CacheSetSessionContextArgs,
        CompoundMemoriesArgs,
        DeleteExpiredMemoriesArgs,
        ExtractSessionLearningsArgs,
        GetContextArgs,
        GetMemoryStatsArgs,
        GetProactiveSuggestionsArgs,
        GraphCreateEventArgs,
        GraphGetContextArgs,
        GraphGetEntityArgs,
        GraphGetEventSequenceArgs,
        GraphGetEventTimelineArgs,
        GraphGetTemporalEventsArgs,
        GraphQueryArgs,
        QueryTemporalArgs,
        SaveMemoryArgs,
        SaveMemoryWithConfidenceArgs,
        SearchMemoryArgs,
    )

    # Extract caller metadata for enforcement
    caller_id = caller.caller_id if caller else "unknown"
    creator = caller.creator if caller else "unknown"
    source = caller.source if caller else "unknown"

    # =========================================================================
    # PRINCIPAL EXTRACTION (fail-closed — no implicit SYSTEM escalation)
    # principal_id MUST come from authenticated caller identity.
    # Bootstrap/health-check flows must explicitly pass SYSTEM_PRINCIPAL_ID
    # at the callsite — MCP layer NEVER injects it.
    # =========================================================================
    principal_id = getattr(caller, "principal_id", None)
    if not (isinstance(principal_id, str) and principal_id.strip()):
        # CallerIdentity (mcp_memory) has caller_id/user_id, not principal_id.
        # Derive a namespaced principal from authenticated identity only.
        # Never inject SYSTEM_PRINCIPAL_ID.
        derived_user = getattr(caller, "user_id", None) if caller else None
        if caller_id == "L":
            principal_id = "agent:l-cto"
        elif caller_id == "C" and isinstance(derived_user, str) and derived_user.strip():
            principal_id = f"user:{derived_user.strip()}"
        else:
            logger.error(
                "mcp_tool_call_missing_or_invalid_principal",
                tool=tool.name,
                caller_id=caller_id,
                principal_id=principal_id,
            )
            raise RuntimeError(
                f"MCP request missing valid principal_id for tool '{tool.name}'."
            )
    else:
        principal_id = principal_id.strip()

    logger.info(
        "mcp_tool_call_principal_resolved",
        tool=tool.name,
        caller_id=caller_id,
        principal_id=principal_id,
    )

    # ADR-0098: project_id from centralized config_constants (single source of truth)
    # On C1: L9_PROJECT_ID=l9-c1, locally defaults to l9-default
    project_id = get_default_project_id()

    # Track execution time for audit
    start_time = time.time()

    result = None
    error = None

    # =============================================================================
    # INPUT VALIDATION: Validate tool arguments using Pydantic models
    # =============================================================================
    # Fail-fast contract: Validate before any processing to catch invalid inputs early
    try:
        if tool.name == "save_memory":
            validated_args = SaveMemoryArgs(**tool.arguments)
        elif tool.name == "search_memory":
            validated_args = SearchMemoryArgs(**tool.arguments)
        elif tool.name == "get_memory_stats":
            validated_args = GetMemoryStatsArgs(**tool.arguments)
        elif tool.name == "delete_expired_memories":
            validated_args = DeleteExpiredMemoriesArgs(**tool.arguments)
        elif tool.name == "compound_memories":
            validated_args = CompoundMemoriesArgs(**tool.arguments)
        elif tool.name == "apply_decay":
            validated_args = ApplyDecayArgs(**tool.arguments)
        elif tool.name == "get_context":
            validated_args = GetContextArgs(**tool.arguments)
        elif tool.name == "extract_session_learnings":
            validated_args = ExtractSessionLearningsArgs(**tool.arguments)
        elif tool.name == "get_proactive_suggestions":
            validated_args = GetProactiveSuggestionsArgs(**tool.arguments)
        elif tool.name == "query_temporal":
            validated_args = QueryTemporalArgs(**tool.arguments)
        elif tool.name == "save_memory_with_confidence":
            validated_args = SaveMemoryWithConfidenceArgs(**tool.arguments)
        # Graph (Neo4j) tools
        elif tool.name == "graph_query":
            validated_args = GraphQueryArgs(**tool.arguments)
        elif tool.name == "graph_get_entity":
            validated_args = GraphGetEntityArgs(**tool.arguments)
        elif tool.name == "graph_get_context":
            validated_args = GraphGetContextArgs(**tool.arguments)
        # Graph Event (Neo4j Event nodes) tools
        elif tool.name == "graph_create_event":
            validated_args = GraphCreateEventArgs(**tool.arguments)
        elif tool.name == "graph_get_event_timeline":
            validated_args = GraphGetEventTimelineArgs(**tool.arguments)
        elif tool.name == "graph_get_temporal_events":
            validated_args = GraphGetTemporalEventsArgs(**tool.arguments)
        elif tool.name == "graph_get_event_sequence":
            validated_args = GraphGetEventSequenceArgs(**tool.arguments)
        # Cache (Redis) tools
        elif tool.name == "cache_get":
            validated_args = CacheGetArgs(**tool.arguments)
        elif tool.name == "cache_set":
            validated_args = CacheSetArgs(**tool.arguments)
        elif tool.name == "cache_get_session_context":
            validated_args = CacheGetSessionContextArgs(**tool.arguments)
        elif tool.name == "cache_set_session_context":
            validated_args = CacheSetSessionContextArgs(**tool.arguments)
        elif tool.name == "cache_delete":
            validated_args = CacheDeleteArgs(**tool.arguments)
        elif tool.name == "cache_keys":
            validated_args = CacheKeysArgs(**tool.arguments)
        else:
            raise ValueError(f"Unknown tool: {tool.name}")
    except ValidationError as e:
        # Fail-fast: Invalid input detected, reject immediately
        error_msg = f"Invalid arguments for tool '{tool.name}': {e.errors()}"
        logger.warning(error_msg, tool_name=tool.name, validation_errors=e.errors())
        raise ValueError(error_msg) from e

    try:
        if tool.name == "save_memory":
            from src.routes.memory_unified import save_memory_handler

            # Use validated_args (already validated by Pydantic above)
            requested_scope = validated_args.scope

            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError(
                    "Cursor cannot write to l-private scope. Only L-CTO can write private memories."
                )

            result = await save_memory_handler(
                user_id=user_id,
                content=validated_args.content,
                kind=validated_args.kind,
                scope=requested_scope,
                duration=validated_args.duration,
                tags=validated_args.tags or [],
                importance=validated_args.importance or 1.0,
                caller_id=caller_id,
                creator=creator,
                source=source,
                substrate_service=substrate_service,  # Pass service for main pipeline
            )
        elif tool.name == "search_memory":
            from src.routes.memory_unified import search_memory_handler

            # Use validated_args (already validated by Pydantic above)
            # ADR-0098: scope defaults from config_constants
            requested_scopes = validated_args.scopes or DEFAULT_SEARCH_SCOPES

            # Enforce: Cursor CANNOT see l-private scope (filter it out)
            if caller_id == "C" and "l-private" in requested_scopes:
                requested_scopes = [s for s in requested_scopes if s != "l-private"]

            # L gets all scopes including l-private
            if caller_id == "L" and "l-private" not in requested_scopes:
                # L can explicitly request l-private, but default includes it
                pass  # Don't auto-add, respect explicit request

            # GMP-JSONB-GOV-FIX: Pass project_id from env var for project isolation
            result = await search_memory_handler(
                user_id=user_id,
                query=validated_args.query,
                scopes=requested_scopes,
                kinds=validated_args.kinds,
                top_k=validated_args.top_k or 5,
                # FIX: threshold=0.0 is valid (no filtering), don't treat as falsy
                threshold=(
                    validated_args.threshold
                    if validated_args.threshold is not None
                    else 0.7
                ),
                duration=validated_args.duration or "all",
                caller_id=caller_id,  # Perplexity: pass caller for audit logging
                project_id=project_id,  # From env: L9_PROJECT_ID
            )
        elif tool.name == "get_memory_stats":
            from src.routes.memory_unified import get_memory_stats

            result = await get_memory_stats(
                user_id=validated_args.user_id,  # This one legitimately uses user_id from args
                duration=validated_args.duration or "all",
            )
        elif tool.name == "delete_expired_memories":
            from src.routes.memory_unified import delete_expired_memories

            result = await delete_expired_memories(
                dry_run=(
                    validated_args.dry_run
                    if validated_args.dry_run is not None
                    else True
                )
            )
        elif tool.name == "compound_memories":
            from src.routes.memory_unified import compound_similar_memories

            result = await compound_similar_memories(
                user_id=user_id,  # Injected from caller identity
                threshold=validated_args.threshold or 0.92,
            )
        elif tool.name == "apply_decay":
            from src.routes.memory_unified import apply_importance_decay

            result = await apply_importance_decay(
                dry_run=(
                    validated_args.dry_run
                    if validated_args.dry_run is not None
                    else True
                )
            )
        # =============================================================================
        # 10x Memory Upgrade Tool Handlers
        # =============================================================================
        elif tool.name == "get_context":
            from src.routes.memory_unified import get_context_injection

            # ADR-0098: scope filtering from config_constants
            allowed_scopes = (
                get_allowed_scopes_for_caller(caller_id) if caller_id == "C" else None
            )

            result = await get_context_injection(
                task_description=validated_args.task_description,
                user_id=user_id,
                top_k=validated_args.top_k or 5,
                include_recent=(
                    validated_args.include_recent
                    if validated_args.include_recent is not None
                    else True
                ),
                kinds=validated_args.kinds,
                allowed_scopes=allowed_scopes,
                caller_id=caller_id,
                creator=creator,
                source=source,
            )
        elif tool.name == "extract_session_learnings":
            from src.routes.memory_unified import extract_session_learnings

            result = await extract_session_learnings(
                user_id=user_id,
                session_id=validated_args.session_id,
                session_summary=validated_args.session_summary,
                key_decisions=validated_args.key_decisions,
                errors_encountered=validated_args.errors_encountered,
                successes=validated_args.successes,
                caller_id=caller_id,
                creator=creator,
                source=source,
            )
        elif tool.name == "get_proactive_suggestions":
            from src.routes.memory_unified import get_proactive_suggestions

            # ADR-0098: scope filtering from config_constants
            allowed_scopes = (
                get_allowed_scopes_for_caller(caller_id) if caller_id == "C" else None
            )

            result = await get_proactive_suggestions(
                current_context=validated_args.current_context,
                user_id=user_id,
                include_error_fixes=(
                    validated_args.include_error_fixes
                    if validated_args.include_error_fixes is not None
                    else True
                ),
                include_preferences=(
                    validated_args.include_preferences
                    if validated_args.include_preferences is not None
                    else True
                ),
                top_k=validated_args.top_k or 3,
                allowed_scopes=allowed_scopes,
            )
        elif tool.name == "query_temporal":
            from src.routes.memory_unified import query_temporal

            # GOVERNANCE: Cursor CANNOT see l-private via temporal queries
            # ADR-0098: scope filtering from config_constants
            allowed_scopes = (
                get_allowed_scopes_for_caller(caller_id) if caller_id == "C" else None
            )

            result = await query_temporal(
                user_id=user_id,
                since=validated_args.since,
                until=validated_args.until,
                kinds=validated_args.kinds,
                operation=validated_args.operation or "changes",
                allowed_scopes=allowed_scopes,  # NEW: scope filter for governance
            )
        elif tool.name == "save_memory_with_confidence":
            from src.routes.memory_unified import save_memory_with_confidence

            # Use validated_args (already validated by Pydantic above)
            requested_scope = validated_args.scope

            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError(
                    "Cursor cannot write to l-private scope. Only L-CTO can write private memories."
                )

            result = await save_memory_with_confidence(
                user_id=user_id,
                content=validated_args.content,
                kind=validated_args.kind,
                scope=requested_scope,
                duration=validated_args.duration,
                confidence=validated_args.confidence or 1.0,
                # Source is enforced server-side, not from client
                source=source,  # From caller identity, not payload
                related_memory_ids=validated_args.related_memory_ids,
                tags=validated_args.tags or [],
                importance=validated_args.importance or 1.0,
                caller_id=caller_id,
                creator=creator,
                substrate_service=substrate_service,  # GMP-89: Pass for main pipeline
            )
        # =============================================================================
        # Graph (Neo4j) Tool Handlers
        # =============================================================================
        elif tool.name == "graph_query":
            # Lazy import Neo4j client from api layer
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    query_result = await client.run_query(
                        query=validated_args.query,
                        parameters=validated_args.parameters,
                    )
                    result = {"success": True, "data": query_result, "available": True}
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "graph_get_entity":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    entity = await client.get_entity(
                        validated_args.entity_type,
                        validated_args.entity_id,
                    )
                    if entity is None:
                        result = {"success": False, "error": "Entity not found"}
                    else:
                        result = {"success": True, "data": entity}
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "graph_get_context":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {
                        "domain": validated_args.domain,
                        "available": False,
                        "entities": [],
                        "relationships": [],
                        "message": "Neo4j not available",
                    }
                else:
                    # Query for domain-related entities
                    query = """
                    MATCH (n)
                    WHERE n.domain = $domain OR n.name CONTAINS $domain OR labels(n)[0] CONTAINS $domain
                    RETURN n, labels(n) as labels
                    LIMIT $limit
                    """
                    entities = await client.run_query(
                        query,
                        {
                            "domain": validated_args.domain,
                            "limit": validated_args.limit or 10,
                        },
                    )

                    # Query for relationships involving domain entities
                    rel_query = """
                    MATCH (a)-[r]->(b)
                    WHERE a.domain = $domain OR b.domain = $domain
                    RETURN type(r) as rel_type, a.id as from_id, b.id as to_id
                    LIMIT $limit
                    """
                    relationships = await client.run_query(
                        rel_query,
                        {
                            "domain": validated_args.domain,
                            "limit": validated_args.limit or 10,
                        },
                    )

                    result = {
                        "domain": validated_args.domain,
                        "available": True,
                        "entities": entities,
                        "relationships": relationships,
                        "count": len(entities),
                    }
            except ImportError:
                result = {
                    "domain": validated_args.domain,
                    "available": False,
                    "entities": [],
                    "relationships": [],
                    "error": "Neo4j client not configured",
                }
            except Exception as e:
                result = {
                    "domain": validated_args.domain,
                    "available": False,
                    "entities": [],
                    "relationships": [],
                    "error": str(e),
                }

        # =============================================================================
        # Graph Event (Neo4j Event nodes) Tool Handlers
        # =============================================================================
        elif tool.name == "graph_create_event":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    event_id = await client.create_event(
                        event_id=validated_args.event_id,
                        event_type=validated_args.event_type,
                        timestamp=validated_args.timestamp,
                        properties=validated_args.properties or {},
                        parent_event_id=validated_args.parent_event_id,
                    )
                    if event_id:
                        result = {
                            "success": True,
                            "event_id": event_id,
                            "event_type": validated_args.event_type,
                            "message": f"Event {event_id} created",
                        }
                    else:
                        result = {"success": False, "error": "Failed to create event"}
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "graph_get_event_timeline":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    events = await client.get_event_timeline(
                        start_time=validated_args.start_time,
                        end_time=validated_args.end_time,
                        event_type=validated_args.event_type,
                        limit=validated_args.limit or 100,
                    )
                    result = {
                        "success": True,
                        "events": events,
                        "count": len(events),
                        "available": True,
                    }
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "graph_get_temporal_events":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    events = await client.get_temporal_events(
                        entity=validated_args.entity,
                        start=validated_args.start,
                        end=validated_args.end,
                    )
                    result = {
                        "success": True,
                        "entity": validated_args.entity,
                        "events": events,
                        "count": len(events),
                        "available": True,
                    }
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "graph_get_event_sequence":
            try:
                from api.memory.graph import get_neo4j

                client = await get_neo4j()
                if client is None or not client.is_available():
                    result = {"error": "Neo4j not available", "available": False}
                else:
                    events = await client.get_event_sequence(
                        entity=validated_args.entity,
                        limit=validated_args.limit or 50,
                    )
                    result = {
                        "success": True,
                        "entity": validated_args.entity,
                        "events": events,
                        "count": len(events),
                        "available": True,
                    }
            except ImportError:
                result = {"error": "Neo4j client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        # =============================================================================
        # Cache (Redis) Tool Handlers
        # =============================================================================
        elif tool.name == "cache_get":
            try:
                import json as json_lib

                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    value = await client.get(validated_args.key)
                    if value is None:
                        result = {"success": False, "error": "Key not found"}
                    else:
                        # Try to parse as JSON
                        try:
                            parsed = json_lib.loads(value)
                            result = {"success": True, "data": parsed}
                        except json_lib.JSONDecodeError:
                            result = {"success": True, "data": value}
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "cache_set":
            try:
                import json as json_lib

                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    # Serialize value to JSON if not string
                    if isinstance(validated_args.value, str):
                        value = validated_args.value
                    else:
                        value = json_lib.dumps(validated_args.value)

                    set_result = await client.set(
                        validated_args.key,
                        value,
                        ttl=validated_args.ttl,
                    )
                    result = {"success": set_result, "key": validated_args.key}
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "cache_get_session_context":
            try:
                import json as json_lib
                import uuid
                from datetime import datetime, timezone

                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    # Generate daily session ID if not provided
                    session_id = validated_args.session_id
                    if not session_id:
                        L9_SESSION_NAMESPACE = uuid.UUID(
                            "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                        )
                        today = datetime.now(UTC).strftime("%Y-%m-%d")
                        session_id = str(
                            uuid.uuid5(L9_SESSION_NAMESPACE, f"l9-session-{today}")
                        )

                    # Namespace by caller (C, L, etc.) so all agents have separate context
                    key = f"l9:session:{caller_id}:{session_id}:context"
                    value = await client.get(key)

                    if value is None:
                        result = {
                            "success": False,
                            "error": "Session context not found",
                            "session_id": session_id,
                        }
                    else:
                        context = json_lib.loads(value)
                        result = {
                            "success": True,
                            "data": context,
                            "session_id": session_id,
                        }
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "cache_set_session_context":
            try:
                import json as json_lib
                import uuid
                from datetime import datetime, timezone

                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    L9_SESSION_NAMESPACE = uuid.UUID(
                        "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                    )
                    session_id = validated_args.session_id
                    if not session_id:
                        today = datetime.now(UTC).strftime("%Y-%m-%d")
                        session_id = str(
                            uuid.uuid5(L9_SESSION_NAMESPACE, f"l9-session-{today}")
                        )
                    # Namespace by caller so all agents (Cursor, L, etc.) have separate context
                    key = f"l9:session:{caller_id}:{session_id}:context"
                    value = json_lib.dumps(validated_args.context)
                    ttl = validated_args.ttl
                    await client.set(key, value, ttl=ttl)
                    result = {
                        "success": True,
                        "session_id": session_id,
                        "key": key,
                        "ttl": ttl,
                    }
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "cache_delete":
            try:
                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    delete_result = await client.delete(validated_args.key)
                    result = {"success": delete_result, "key": validated_args.key}
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        elif tool.name == "cache_keys":
            try:
                from api.memory.cache import get_redis

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    keys = await client.keys(validated_args.pattern)
                    result = {"success": True, "keys": keys, "count": len(keys)}
            except ImportError:
                result = {"error": "Redis client not configured", "available": False}
            except Exception as e:
                result = {"error": str(e), "available": False}

        else:
            raise ValueError(f"Unknown tool: {tool.name}")

        # Calculate execution time
        duration_ms = (time.time() - start_time) * 1000

        # GOVERNANCE: Mandatory audit logging with fail-closed semantics
        # When GOVERNANCE_HARDENING_ENABLED=True, audit failures reject the operation
        if settings.GOVERNANCE_HARDENING_ENABLED:
            from src.audit import get_audit_logger

            audit_logger = get_audit_logger(execute)
            await audit_logger.log(
                tool_name=tool.name,
                agent_id=user_id,
                caller_id=caller_id,
                project_id=project_id,
                input_data=tool.arguments,
                output_data=result if result else {"error": "No result"},
                duration_ms=duration_ms,
                error=None,
            )
            # If audit fails, AuditLogger raises RuntimeError and request fails
        else:
            # Legacy mode: Best-effort audit (silent failures)
            try:
                await execute(
                    """
                    INSERT INTO tool_audit_log (
                        tool_name, agent_id, caller, project_id,
                        input_data, output_data, duration_ms, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    """,
                    tool.name,
                    user_id,
                    caller_id,
                    project_id,
                    json.dumps(tool.arguments),
                    (
                        json.dumps(result)
                        if result
                        else json.dumps({"error": "No result"})
                    ),
                    duration_ms,
                )
            except Exception as audit_err:
                logger.debug(
                    f"Audit logging skipped (table may not exist): {audit_err}"
                )

        return result

    except Exception as e:
        # Calculate execution time even on error
        duration_ms = (time.time() - start_time) * 1000
        error = str(e)

        # GOVERNANCE: Mandatory error audit logging
        if settings.GOVERNANCE_HARDENING_ENABLED:
            try:
                from src.audit import get_audit_logger

                audit_logger = get_audit_logger(execute)
                await audit_logger.log(
                    tool_name=tool.name,
                    agent_id=user_id,
                    caller_id=caller_id,
                    project_id=project_id,
                    input_data=tool.arguments,
                    output_data={"error": error},
                    duration_ms=duration_ms,
                    error=error,
                )
            except Exception as audit_err:
                # If mandatory audit fails on error path, log and continue
                # (don't mask the original error)
                logger.critical(
                    "AUDIT FAILURE on error path",
                    audit_error=str(audit_err),
                    original_error=error,
                )
        else:
            # Legacy mode: Best-effort audit
            try:
                await execute(
                    """
                    INSERT INTO tool_audit_log (
                        tool_name, agent_id, caller, project_id,
                        input_data, output_data, duration_ms, error, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    tool.name,
                    user_id,
                    caller_id,
                    project_id,
                    json.dumps(tool.arguments),
                    json.dumps({"error": error}),
                    duration_ms,
                    error,
                )
            except Exception as audit_err:
                logger.debug(
                    f"Audit logging skipped (table may not exist): {audit_err}"
                )

        raise


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["api.memory.cache", "api.memory.graph"],
    "tags": [
        "api",
        "async",
        "cache",
        "caching",
        "data-models",
        "debugging",
        "graph-db",
        "integration",
        "logging",
        "messaging",
    ],
    "keywords": ["handle", "mcp", "server", "tool", "tools"],
    "business_value": "Provides mcp server components including MCPTool, MCPToolCall",
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
