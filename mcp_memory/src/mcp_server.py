"""
MCP (Model Context Protocol) Server Implementation.
"""

import structlog
from typing import Any, Dict, List
from pydantic import BaseModel, ValidationError
from src.config import settings

logger = structlog.get_logger(__name__)


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


def get_mcp_tools() -> List[MCPTool]:
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
                        "enum": ["developer", "l-private", "global"],
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
                            "enum": ["developer", "l-private", "global"],
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
                        "enum": ["developer", "l-private", "global"],
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
            description="Get Cursor session context from Redis cache. Returns fast-access session state.",
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
    ]


async def handle_tool_call(
    tool: MCPToolCall,
    user_id: str,
    caller: Any = None,
    substrate_service: Any = None,  # Optional: MemorySubstrateService for main pipeline
) -> Dict[str, Any]:
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
    import time
    import json
    from src.db import execute
    from src.models import (
        SaveMemoryArgs,
        SearchMemoryArgs,
        GetMemoryStatsArgs,
        DeleteExpiredMemoriesArgs,
        CompoundMemoriesArgs,
        ApplyDecayArgs,
        GetContextArgs,
        ExtractSessionLearningsArgs,
        GetProactiveSuggestionsArgs,
        QueryTemporalArgs,
        SaveMemoryWithConfidenceArgs,
        # Graph (Neo4j) tool args
        GraphQueryArgs,
        GraphGetEntityArgs,
        GraphGetContextArgs,
        # Cache (Redis) tool args
        CacheGetArgs,
        CacheSetArgs,
        CacheGetSessionContextArgs,
    )

    # Extract caller metadata for enforcement
    caller_id = caller.caller_id if caller else "unknown"
    creator = caller.creator if caller else "unknown"
    source = caller.source if caller else "unknown"

    # Determine project_id (default: 'l9' for developer/l-private scope)
    project_id = "l9"  # Default for L9 repo

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
        # Cache (Redis) tools
        elif tool.name == "cache_get":
            validated_args = CacheGetArgs(**tool.arguments)
        elif tool.name == "cache_set":
            validated_args = CacheSetArgs(**tool.arguments)
        elif tool.name == "cache_get_session_context":
            validated_args = CacheGetSessionContextArgs(**tool.arguments)
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
            requested_scopes = validated_args.scopes or ["developer", "global"]

            # Enforce: Cursor CANNOT see l-private scope (filter it out)
            if caller_id == "C" and "l-private" in requested_scopes:
                requested_scopes = [s for s in requested_scopes if s != "l-private"]

            # L gets all scopes including l-private
            if caller_id == "L" and "l-private" not in requested_scopes:
                # L can explicitly request l-private, but default includes it
                pass  # Don't auto-add, respect explicit request

            result = await search_memory_handler(
                user_id=user_id,
                query=validated_args.query,
                scopes=requested_scopes,
                kinds=validated_args.kinds,
                top_k=validated_args.top_k or 5,
                threshold=validated_args.threshold or 0.7,
                duration=validated_args.duration or "all",
                caller_id=caller_id,  # Perplexity: pass caller for audit logging
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
                dry_run=validated_args.dry_run
                if validated_args.dry_run is not None
                else True
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
                dry_run=validated_args.dry_run
                if validated_args.dry_run is not None
                else True
            )
        # =============================================================================
        # 10x Memory Upgrade Tool Handlers
        # =============================================================================
        elif tool.name == "get_context":
            from src.routes.memory_unified import get_context_injection

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None

            result = await get_context_injection(
                task_description=validated_args.task_description,
                user_id=user_id,
                top_k=validated_args.top_k or 5,
                include_recent=validated_args.include_recent
                if validated_args.include_recent is not None
                else True,
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

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None

            result = await get_proactive_suggestions(
                current_context=validated_args.current_context,
                user_id=user_id,
                include_error_fixes=validated_args.include_error_fixes
                if validated_args.include_error_fixes is not None
                else True,
                include_preferences=validated_args.include_preferences
                if validated_args.include_preferences is not None
                else True,
                top_k=validated_args.top_k or 3,
                allowed_scopes=allowed_scopes,
            )
        elif tool.name == "query_temporal":
            from src.routes.memory_unified import query_temporal

            # GOVERNANCE: Cursor CANNOT see l-private via temporal queries
            # Scope filtering enforced at SQL level using = ANY($N)
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None

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
        # Cache (Redis) Tool Handlers
        # =============================================================================
        elif tool.name == "cache_get":
            try:
                from api.memory.cache import get_redis
                import json as json_lib

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
                from api.memory.cache import get_redis
                import json as json_lib

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
                from api.memory.cache import get_redis
                import json as json_lib
                import uuid
                from datetime import datetime, timezone

                client = await get_redis()
                if client is None or not client.is_available():
                    result = {"error": "Redis not available", "available": False}
                else:
                    # Generate daily session ID if not provided
                    session_id = validated_args.session_id
                    if not session_id:
                        # Use same logic as cursor_memory_client.py
                        CURSOR_SESSION_NAMESPACE = uuid.UUID(
                            "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                        )
                        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        session_id = str(
                            uuid.uuid5(
                                CURSOR_SESSION_NAMESPACE, f"cursor-session-{today}"
                            )
                        )

                    key = f"cursor:session:{session_id}:context"
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
                    json.dumps(result)
                    if result
                    else json.dumps({"error": "No result"}),
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
