"""
MCP (Model Context Protocol) Server Implementation.
"""

import structlog
from typing import Any, Dict, List
from pydantic import BaseModel, ValidationError

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
                    "scope": {"type": "string", "enum": ["developer", "l-private", "global"]},
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
                                "igor:context"
                            ]
                        },
                        "description": "L9 hierarchical memory categories (domain:specificity)"
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
                    "scopes": {"type": "array", "items": {"type": "string", "enum": ["developer", "l-private", "global"]}},
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
                        "enum": ["preference", "fact", "context", "error", "success", "learning", "decision"],
                    },
                    "scope": {"type": "string", "enum": ["developer", "l-private", "global"]},
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

            requested_scope = tool.arguments.get("scope", "developer")  # MCP scope: developer/l-private/global
            
            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError("Cursor cannot write to l-private scope. Only L-CTO can write private memories.")
            
            result = await save_memory_handler(
                user_id=user_id,
                content=tool.arguments.get("content"),
                kind=tool.arguments.get("kind"),
                scope=requested_scope,
                duration=tool.arguments.get("duration"),
                tags=tool.arguments.get("tags", []),
                importance=tool.arguments.get("importance", 1.0),
                caller_id=caller_id,
                creator=creator,
                source=source,
                substrate_service=substrate_service,  # Pass service for main pipeline
            )
        elif tool.name == "search_memory":
            from src.routes.memory_unified import search_memory_handler

            requested_scopes = tool.arguments.get("scopes", ["developer", "global"])  # MCP scopes
            
            # Enforce: Cursor CANNOT see l-private scope (filter it out)
            if caller_id == "C" and "l-private" in requested_scopes:
                requested_scopes = [s for s in requested_scopes if s != "l-private"]
            
            # L gets all scopes including l-private
            if caller_id == "L" and "l-private" not in requested_scopes:
                # L can explicitly request l-private, but default includes it
                pass  # Don't auto-add, respect explicit request
            
            result = await search_memory_handler(
                user_id=user_id,
                query=tool.arguments.get("query"),
                scopes=requested_scopes,
                kinds=tool.arguments.get("kinds"),
                top_k=tool.arguments.get("top_k", 5),
                threshold=tool.arguments.get("threshold", 0.7),
                duration=tool.arguments.get("duration", "all"),
                caller_id=caller_id,  # Perplexity: pass caller for audit logging
            )
        elif tool.name == "get_memory_stats":
            from src.routes.memory_unified import get_memory_stats

            result = await get_memory_stats(
                user_id=tool.arguments.get("user_id"),
                duration=tool.arguments.get("duration", "all"),
            )
        elif tool.name == "delete_expired_memories":
            from src.routes.memory_unified import delete_expired_memories

            result = await delete_expired_memories(
                dry_run=tool.arguments.get("dry_run", True)
            )
        elif tool.name == "compound_memories":
            from src.routes.memory_unified import compound_similar_memories

            result = await compound_similar_memories(
                user_id=tool.arguments.get("user_id"),
                threshold=tool.arguments.get("threshold", 0.92),
            )
        elif tool.name == "apply_decay":
            from src.routes.memory_unified import apply_importance_decay

            result = await apply_importance_decay(dry_run=tool.arguments.get("dry_run", True))
        # =============================================================================
        # 10x Memory Upgrade Tool Handlers
        # =============================================================================
        elif tool.name == "get_context":
            from src.routes.memory_unified import get_context_injection

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None
            
            result = await get_context_injection(
                task_description=tool.arguments.get("task_description"),
                user_id=user_id,
                top_k=tool.arguments.get("top_k", 5),
                include_recent=tool.arguments.get("include_recent", True),
                kinds=tool.arguments.get("kinds"),
                allowed_scopes=allowed_scopes,
                caller_id=caller_id,
                creator=creator,
                source=source,
            )
        elif tool.name == "extract_session_learnings":
            from src.routes.memory_unified import extract_session_learnings

            result = await extract_session_learnings(
                user_id=user_id,
                session_id=tool.arguments.get("session_id"),
                session_summary=tool.arguments.get("session_summary"),
                key_decisions=tool.arguments.get("key_decisions"),
                errors_encountered=tool.arguments.get("errors_encountered"),
                successes=tool.arguments.get("successes"),
                caller_id=caller_id,
                creator=creator,
                source=source,
            )
        elif tool.name == "get_proactive_suggestions":
            from src.routes.memory_unified import get_proactive_suggestions

            # Cursor gets filtered scopes (no l-private), L gets all
            allowed_scopes = ["developer", "global"] if caller_id == "C" else None
            
            result = await get_proactive_suggestions(
                current_context=tool.arguments.get("current_context"),
                user_id=user_id,
                include_error_fixes=tool.arguments.get("include_error_fixes", True),
                include_preferences=tool.arguments.get("include_preferences", True),
                top_k=tool.arguments.get("top_k", 3),
                allowed_scopes=allowed_scopes,
            )
        elif tool.name == "query_temporal":
            from src.routes.memory_unified import query_temporal

            result = await query_temporal(
                user_id=user_id,
                since=tool.arguments.get("since"),
                until=tool.arguments.get("until"),
                kinds=tool.arguments.get("kinds"),
                operation=tool.arguments.get("operation", "changes"),
            )
        elif tool.name == "save_memory_with_confidence":
            from src.routes.memory_unified import save_memory_with_confidence

            requested_scope = tool.arguments.get("scope", "developer")  # MCP scope
            
            # Enforce: Cursor CANNOT write l-private scope
            if caller_id == "C" and requested_scope == "l-private":
                raise ValueError("Cursor cannot write to l-private scope. Only L-CTO can write private memories.")
            
            result = await save_memory_with_confidence(
                user_id=user_id,
                content=tool.arguments.get("content"),
                kind=tool.arguments.get("kind"),
                scope=requested_scope,
                duration=tool.arguments.get("duration"),
                confidence=tool.arguments.get("confidence", 1.0),
                # Source is enforced server-side, not from client
                source=source,  # From caller identity, not payload
                related_memory_ids=tool.arguments.get("related_memory_ids"),
                tags=tool.arguments.get("tags", []),
                importance=tool.arguments.get("importance", 1.0),
                caller_id=caller_id,
                creator=creator,
            )
        else:
            raise ValueError(f"Unknown tool: {tool.name}")
        
        # Calculate execution time
        duration_ms = (time.time() - start_time) * 1000
        
        # Audit logging: Log to tool_audit_log (L9 substrate)
        try:
            await execute(
                """
                INSERT INTO tool_audit_log (
                    tool_name, agent_id, caller, project_id,
                    input_data, output_data, duration_ms, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                tool.name,  # tool_name
                user_id,  # agent_id
                caller_id,  # caller ('L' or 'C')
                project_id,  # project_id ('l9' or NULL)
                json.dumps(tool.arguments),  # input_data
                json.dumps(result) if result else json.dumps({"error": "No result"}),  # output_data
                duration_ms,  # duration_ms
            )
        except Exception as audit_err:
            # Don't fail if tool_audit_log table doesn't exist yet (migration 0013 may not be applied)
            logger.debug(f"Audit logging skipped (table may not exist): {audit_err}")
        
        return result
        
    except Exception as e:
        # Calculate execution time even on error
        duration_ms = (time.time() - start_time) * 1000
        error = str(e)
        
        # Audit logging: Log error to tool_audit_log
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
            logger.debug(f"Audit logging skipped (table may not exist): {audit_err}")
        
        raise
