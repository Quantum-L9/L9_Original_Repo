"""
OpenAI function-calling schemas for L9 tools.

Agent-agnostic. Used by sync_runtime_tools_to_primary() to populate
ToolMetadata.input_schema in the base registry.

ADR-0094: Extracted from registry_adapter.py _get_tool_schema() and
_get_l_tool_schema_for_registry() to decouple from L-CTO-specific code.
"""

from __future__ import annotations

__dora_meta__ = {
    "component_name": "Tool Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-13T00:00:00Z",
    "updated_at": "2026-02-13T00:00:00Z",
    "layer": "config",
    "domain": "tools",
    "module_name": "tool_schemas",
    "type": "data",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.tools.registry_adapter"],
    },
}

# =============================================================================
# Canonical tool schemas (OpenAI function-calling format)
# =============================================================================

TOOL_SCHEMAS: dict[str, dict] = {
    # =========================================================================
    # Memory Tools
    # =========================================================================
    "memory_search": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query",
            },
            "segment": {
                "type": "string",
                "description": "Memory segment: 'all', 'governance', 'project', 'session'",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (1-100)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
    "memory_write": {
        "type": "object",
        "properties": {
            "packet": {
                "type": "object",
                "description": "Packet data to write",
            },
            "segment": {
                "type": "string",
                "description": "Target memory segment",
            },
        },
        "required": ["packet", "segment"],
    },
    "memory_get_packet": {
        "type": "object",
        "properties": {
            "packet_id": {
                "type": "string",
                "description": "UUID of packet to retrieve",
            },
        },
        "required": ["packet_id"],
    },
    "memory_query_packets": {
        "type": "object",
        "properties": {
            "filters": {"type": "object", "description": "Filter criteria"},
            "limit": {
                "type": "integer",
                "description": "Max results",
                "default": 50,
            },
        },
        "required": ["filters"],
    },
    "memory_search_by_thread": {
        "type": "object",
        "properties": {
            "thread_id": {
                "type": "string",
                "description": "Thread/conversation ID",
            },
            "limit": {
                "type": "integer",
                "description": "Max results",
                "default": 50,
            },
        },
        "required": ["thread_id"],
    },
    "memory_search_by_type": {
        "type": "object",
        "properties": {
            "packet_type": {
                "type": "string",
                "description": "Packet kind (REASONING, TOOL_CALL, etc.)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results",
                "default": 50,
            },
        },
        "required": ["packet_type"],
    },
    "memory_get_events": {
        "type": "object",
        "properties": {
            "event_type": {
                "type": "string",
                "description": "Optional event type filter",
            },
            "limit": {
                "type": "integer",
                "description": "Max results",
                "default": 50,
            },
        },
        "required": [],
    },
    "memory_get_reasoning_traces": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Optional task ID filter",
            },
            "limit": {
                "type": "integer",
                "description": "Max traces",
                "default": 20,
            },
        },
        "required": [],
    },
    "memory_get_facts": {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "Subject to query facts about",
            },
            "limit": {
                "type": "integer",
                "description": "Max facts",
                "default": 20,
            },
        },
        "required": ["subject"],
    },
    "memory_write_insight": {
        "type": "object",
        "properties": {
            "insight": {
                "type": "string",
                "description": "Insight text to store",
            },
            "category": {
                "type": "string",
                "description": "Category (governance, project, session)",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence 0-1",
                "default": 0.8,
            },
        },
        "required": ["insight", "category"],
    },
    "memory_embed_text": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to embed"},
        },
        "required": ["text"],
    },
    "memory_hybrid_search": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {
                "type": "integer",
                "description": "Max results",
                "default": 10,
            },
            "filters": {"type": "object", "description": "Optional filters"},
        },
        "required": ["query"],
    },
    "memory_fetch_lineage": {
        "type": "object",
        "properties": {
            "packet_id": {"type": "string", "description": "Packet UUID"},
            "direction": {
                "type": "string",
                "description": "ancestors or descendants",
                "default": "ancestors",
            },
            "max_depth": {
                "type": "integer",
                "description": "Max traversal depth",
                "default": 5,
            },
        },
        "required": ["packet_id"],
    },
    "memory_fetch_thread": {
        "type": "object",
        "properties": {
            "thread_id": {"type": "string", "description": "Thread ID"},
            "limit": {
                "type": "integer",
                "description": "Max packets",
                "default": 100,
            },
        },
        "required": ["thread_id"],
    },
    "memory_fetch_facts_api": {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Subject filter"},
            "predicate": {"type": "string", "description": "Predicate filter"},
            "limit": {
                "type": "integer",
                "description": "Max facts",
                "default": 50,
            },
        },
        "required": [],
    },
    "memory_fetch_insights": {
        "type": "object",
        "properties": {
            "packet_id": {
                "type": "string",
                "description": "Source packet filter",
            },
            "insight_type": {
                "type": "string",
                "description": "Insight type filter",
            },
            "limit": {
                "type": "integer",
                "description": "Max insights",
                "default": 50,
            },
        },
        "required": [],
    },
    "memory_gc_stats": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "memory_get_checkpoint": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "Agent ID"},
        },
        "required": [],
    },
    "memory_trigger_world_model_update": {
        "type": "object",
        "properties": {
            "insights": {"type": "array", "description": "List of insight dicts"},
        },
        "required": ["insights"],
    },
    "memory_health_check": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    # =========================================================================
    # Execution Tools (high-risk)
    # =========================================================================
    "gmp_run": {
        "type": "object",
        "properties": {
            "gmp_id": {
                "type": "string",
                "description": "GMP identifier (e.g., 'GMP-L-CTO-P0-TOOLS')",
            },
            "params": {
                "type": "object",
                "description": "GMP execution parameters",
                "default": {},
            },
        },
        "required": ["gmp_id"],
    },
    "git_commit": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to commit (empty = all staged)",
                "default": [],
            },
        },
        "required": ["message"],
    },
    "mac_agent_exec_task": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (5-300)",
                "default": 30,
            },
        },
        "required": ["command"],
    },
    # =========================================================================
    # MCP Tools
    # =========================================================================
    "mcp_list_servers": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "mcp_list_tools": {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "MCP server identifier: 'github', 'notion', 'filesystem', 'memory', 'l9-memory'",
            },
        },
        "required": ["server_id"],
    },
    "mcp_call_tool": {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "MCP server identifier: 'github', 'notion', 'filesystem', etc.",
            },
            "tool_name": {
                "type": "string",
                "description": "Tool name (e.g., 'create_issue', 'search', 'read_file')",
            },
            "arguments": {
                "type": "object",
                "description": "Tool arguments",
                "default": {},
            },
        },
        "required": ["server_id", "tool_name"],
    },
    "mcp_discover_and_register": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "mcp_start_server": {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "MCP server ID to start",
            },
        },
        "required": ["server_id"],
    },
    "mcp_stop_server": {
        "type": "object",
        "properties": {
            "server_id": {"type": "string", "description": "MCP server ID to stop"},
        },
        "required": ["server_id"],
    },
    "mcp_stop_all_servers": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    # =========================================================================
    # World Model Tools
    # =========================================================================
    "world_model_query": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "description": "Query type: 'get_entity', 'list_entities', 'state_version'",
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "default": {},
            },
        },
        "required": ["query_type"],
    },
    "world_model_get_entity": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "description": "Entity ID"},
        },
        "required": ["entity_id"],
    },
    "world_model_list_entities": {
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "description": "Entity type filter",
            },
            "min_confidence": {
                "type": "number",
                "description": "Min confidence",
            },
            "limit": {
                "type": "integer",
                "description": "Max entities",
                "default": 50,
            },
        },
        "required": [],
    },
    "world_model_snapshot": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Snapshot description",
            },
        },
        "required": [],
    },
    "world_model_list_snapshots": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max snapshots",
                "default": 20,
            },
        },
        "required": [],
    },
    "world_model_send_insights": {
        "type": "object",
        "properties": {
            "insights": {"type": "array", "description": "List of insights"},
        },
        "required": ["insights"],
    },
    "world_model_get_state_version": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "world_model_restore": {
        "type": "object",
        "properties": {
            "snapshot_id": {
                "type": "string",
                "description": "Snapshot ID to restore",
            },
        },
        "required": ["snapshot_id"],
    },
    "world_model_list_updates": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max updates to return"},
        },
        "required": [],
    },
    # =========================================================================
    # Kernel / Plan Tools
    # =========================================================================
    "kernel_read": {
        "type": "object",
        "properties": {
            "kernel_name": {
                "type": "string",
                "description": "Kernel identifier: 'identity', 'safety', 'execution', etc.",
            },
            "property": {
                "type": "string",
                "description": "Property to read from kernel",
            },
        },
        "required": ["kernel_name", "property"],
    },
    "long_plan_execute": {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "Plan identifier",
            },
            "params": {
                "type": "object",
                "description": "Execution parameters",
                "default": {},
            },
        },
        "required": ["plan_id"],
    },
    "long_plan_simulate": {
        "type": "object",
        "properties": {
            "plan_id": {
                "type": "string",
                "description": "Plan identifier",
            },
            "params": {
                "type": "object",
                "description": "Simulation parameters",
                "default": {},
            },
        },
        "required": ["plan_id"],
    },
    # =========================================================================
    # Neo4j Tools
    # =========================================================================
    "neo4j_query": {
        "type": "object",
        "properties": {
            "cypher": {
                "type": "string",
                "description": "Cypher query to run against Neo4j graph",
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "default": {},
            },
        },
        "required": ["cypher"],
    },
    # =========================================================================
    # Redis Tools
    # =========================================================================
    "redis_get": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Redis key to retrieve",
            },
        },
        "required": ["key"],
    },
    "redis_set": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Redis key"},
            "value": {"type": "string", "description": "Value to store"},
            "ttl_seconds": {
                "type": "integer",
                "description": "Optional TTL in seconds",
            },
        },
        "required": ["key", "value"],
    },
    "redis_keys": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Key pattern (e.g., 'agent:*')",
                "default": "*",
            },
        },
        "required": [],
    },
    "redis_delete": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to delete"},
        },
        "required": ["key"],
    },
    "redis_enqueue_task": {
        "type": "object",
        "properties": {
            "queue_name": {"type": "string", "description": "Queue name"},
            "task_data": {"type": "object", "description": "Task payload"},
            "priority": {
                "type": "integer",
                "description": "Priority",
                "default": 0,
            },
        },
        "required": ["queue_name", "task_data"],
    },
    "redis_dequeue_task": {
        "type": "object",
        "properties": {
            "queue_name": {"type": "string", "description": "Queue name"},
        },
        "required": ["queue_name"],
    },
    "redis_queue_size": {
        "type": "object",
        "properties": {
            "queue_name": {"type": "string", "description": "Queue name"},
        },
        "required": ["queue_name"],
    },
    "redis_get_task_context": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"},
        },
        "required": ["task_id"],
    },
    "redis_set_task_context": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"},
            "context": {"type": "object", "description": "Context data"},
            "ttl_seconds": {
                "type": "integer",
                "description": "TTL",
                "default": 3600,
            },
        },
        "required": ["task_id", "context"],
    },
    "redis_get_rate_limit": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Rate limit key"},
        },
        "required": ["key"],
    },
    "redis_set_rate_limit": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Rate limit key"},
            "count": {"type": "integer", "description": "Count value to set"},
            "ttl_seconds": {"type": "integer", "description": "TTL in seconds"},
        },
        "required": ["key", "count"],
    },
    "redis_increment_rate_limit": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Rate limit key"},
            "amount": {"type": "integer", "description": "Amount to increment"},
        },
        "required": ["key"],
    },
    "redis_decrement_rate_limit": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Rate limit key"},
            "amount": {"type": "integer", "description": "Amount to decrement"},
        },
        "required": ["key"],
    },
    # =========================================================================
    # Tool Graph Introspection
    # =========================================================================
    "tools_list_all": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "tools_list_enabled": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "tools_get_metadata": {
        "type": "object",
        "properties": {
            "tool_id": {"type": "string", "description": "Tool ID"},
        },
        "required": ["tool_id"],
    },
    "tools_get_schema": {
        "type": "object",
        "properties": {
            "tool_id": {"type": "string", "description": "Tool ID"},
        },
        "required": ["tool_id"],
    },
    "tools_get_by_type": {
        "type": "object",
        "properties": {
            "tool_type": {"type": "string", "description": "Tool type"},
        },
        "required": ["tool_type"],
    },
    "tools_get_for_role": {
        "type": "object",
        "properties": {
            "role": {"type": "string", "description": "Role identifier"},
        },
        "required": ["role"],
    },
    "tools_get_api_dependents": {
        "type": "object",
        "properties": {
            "api_name": {
                "type": "string",
                "description": "API name (e.g., GitHub, OpenAI)",
            },
        },
        "required": ["api_name"],
    },
    "tools_get_dependencies": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Tool name"},
        },
        "required": ["tool_name"],
    },
    "tools_get_blast_radius": {
        "type": "object",
        "properties": {
            "api_name": {"type": "string", "description": "API name"},
        },
        "required": ["api_name"],
    },
    "tools_detect_circular_deps": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "tools_get_catalog": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    # =========================================================================
    # Symbolic Computation Tools
    # =========================================================================
    "symbolic_compute": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Symbolic mathematical expression",
            },
            "variables": {
                "type": "object",
                "description": "Variable substitutions",
                "default": {},
            },
        },
        "required": ["expression"],
    },
    "symbolic_codegen": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Symbolic expression to compile",
            },
            "language": {
                "type": "string",
                "description": "Target language: 'python', 'c', 'fortran'",
                "default": "python",
            },
        },
        "required": ["expression"],
    },
    "symbolic_optimize": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Symbolic expression to optimize",
            },
        },
        "required": ["expression"],
    },
    # =========================================================================
    # Simulation
    # =========================================================================
    "simulation": {
        "type": "object",
        "properties": {
            "graph_data": {
                "type": "object",
                "description": "IR graph data from IRGenerator.to_dict()",
            },
            "scenario_params": {
                "type": "object",
                "description": "Scenario configuration",
                "default": {},
            },
            "mode": {
                "type": "string",
                "description": "Simulation mode: 'fast', 'standard', 'thorough'",
                "default": "standard",
            },
        },
        "required": ["graph_data"],
    },
    # =========================================================================
    # Research Tools
    # =========================================================================
    "perplexity_search": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
        },
        "required": ["query"],
    },
    "http_request": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to request",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "default": "GET",
            },
            "body": {
                "type": "object",
                "description": "Request body (for POST/PUT)",
            },
        },
        "required": ["url"],
    },
    "mock_search": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
        },
        "required": ["query"],
    },
    "research_agent_synthesize": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Research topic to synthesize (required)",
            },
            "context": {
                "type": "object",
                "description": "Optional additional context as key-value pairs",
            },
        },
        "required": ["topic"],
    },
    "research_agent_discover": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Research topic (required)",
            },
            "domain": {
                "type": "string",
                "description": "Research domain (default: general)",
            },
            "stages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Stages to run: landscape, deep_dive, comparative, gaps, hypotheses",
            },
        },
        "required": ["topic"],
    },
    "research_agent_generate_spec": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Module topic (required)",
            },
            "description": {
                "type": "string",
                "description": "Module description",
            },
            "run_synthesis_first": {
                "type": "boolean",
                "description": "Run synthesis before spec generation (default: true)",
            },
        },
        "required": ["topic"],
    },
    # =========================================================================
    # Reflection Tools
    # =========================================================================
    "reflection_agent_reflect": {
        "type": "object",
        "properties": {
            "history": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Execution history to reflect on (required)",
            },
            "focus": {
                "type": "string",
                "description": "Focus area: general, failures, patterns (default: general)",
            },
            "goals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Goals to evaluate against",
            },
        },
        "required": ["history"],
    },
    "reflection_agent_analyze_failure": {
        "type": "object",
        "properties": {
            "failure_context": {
                "type": "object",
                "description": "Context of the failure (required)",
            },
            "error": {
                "type": "string",
                "description": "Error message (required)",
            },
            "stack_trace": {
                "type": "string",
                "description": "Optional stack trace",
            },
        },
        "required": ["failure_context", "error"],
    },
    "reflection_agent_compare_approaches": {
        "type": "object",
        "properties": {
            "approach_a": {
                "type": "object",
                "description": "First approach to compare (required)",
            },
            "approach_b": {
                "type": "object",
                "description": "Second approach to compare (required)",
            },
            "criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Comparison criteria (required)",
            },
        },
        "required": ["approach_a", "approach_b", "criteria"],
    },
    "reflection_agent_extract_patterns": {
        "type": "object",
        "properties": {
            "examples": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Examples to analyze (required, min 2)",
            },
        },
        "required": ["examples"],
    },
    "reflection_agent_generate_improvements": {
        "type": "object",
        "properties": {
            "current_performance": {
                "type": "object",
                "description": "Current performance metrics (required)",
            },
            "goals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Improvement goals (required)",
            },
        },
        "required": ["current_performance", "goals"],
    },
}


def get_tool_schema(tool_id: str) -> dict:
    """Look up a tool schema by ID. Returns empty schema if not found."""
    return TOOL_SCHEMAS.get(tool_id, {"type": "object", "properties": {}})


# ============================================================================
# DORA FOOTER META
# ============================================================================
__dora_footer__ = {
    "component_id": "CFG-TOOL-SCHEMAS-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": False,
    "dependencies": [],
    "tags": ["config", "tools", "schemas", "openai"],
    "keywords": ["schema", "function-calling", "openai", "tool"],
    "business_value": "Canonical tool schemas for OpenAI function-calling, decoupled from agent-specific code.",
    "last_modified": "2026-02-13T00:00:00Z",
    "modified_by": "ADR-0094 migration",
    "change_summary": "Extracted from registry_adapter.py _get_tool_schema and _get_l_tool_schema_for_registry",
}
