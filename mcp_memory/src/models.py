"""
Request/response models.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Models",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "data_models",
    "module_name": "models",
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

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SaveMemoryRequest(BaseModel):
    content: str
    kind: str
    scope: str = "user"
    duration: str
    user_id: str
    tags: list[str] | None = None
    importance: float | None = 1.0
    metadata: dict[str, Any] | None = None


class MemoryResponse(BaseModel):
    id: int
    user_id: str
    kind: str
    content: str
    importance: float
    tags: list[str] | None = None
    created_at: datetime
    similarity: float | None = None


class SearchMemoryRequest(BaseModel):
    query: str
    user_id: str
    scopes: list[str] | None = ["user", "project", "global"]
    kinds: list[str] | None = None
    top_k: int | None = 5
    threshold: float | None = 0.7
    duration: str | None = "all"
    track_access: bool | None = False


class SearchMemoryResponse(BaseModel):
    results: list[MemoryResponse]
    query_embedding_time_ms: float
    search_time_ms: float
    total_results: int


class MemoryStatsResponse(BaseModel):
    short_term_count: int
    medium_term_count: int
    long_term_count: int
    total_count: int
    unique_users: int
    avg_importance: float


class CompoundResult(BaseModel):
    memories_analyzed: int
    clusters_found: int
    memories_merged: int
    importance_boosted: int


# =============================================================================
# Enhanced Memory Models (10x Upgrade)
# =============================================================================


class ContextInjectionRequest(BaseModel):
    """Request for auto context injection before a task."""

    task_description: str
    user_id: str
    top_k: int | None = 5
    include_recent: bool | None = True  # Include last 24h context
    kinds: list[str] | None = None  # Filter by memory kinds


class ContextInjectionResponse(BaseModel):
    """Context memories to inject into system prompt."""

    memories: list[MemoryResponse]
    recent_context: list[MemoryResponse]
    total_injected: int
    retrieval_time_ms: float


class SessionLearningRequest(BaseModel):
    """Request to extract learnings from a session."""

    user_id: str
    session_id: str
    session_summary: str  # What happened this session
    key_decisions: list[str] | None = None
    errors_encountered: list[str] | None = None
    successes: list[str] | None = None


class SessionLearningResponse(BaseModel):
    """Learnings extracted and stored from session."""

    learnings_stored: int
    memory_ids: list[int]
    kinds_created: list[str]


class ProactiveRecallRequest(BaseModel):
    """Request for proactive memory suggestions based on patterns."""

    current_context: str  # What user is currently working on
    user_id: str
    include_error_fixes: bool | None = True
    include_preferences: bool | None = True
    top_k: int | None = 3


class ProactiveRecallResponse(BaseModel):
    """Proactive suggestions surfaced from memory."""

    suggestions: list[MemoryResponse]
    error_fix_pairs: list[dict[str, Any]]  # {error: str, fix: str, confidence: float}
    relevant_preferences: list[MemoryResponse]
    recall_time_ms: float


class TemporalQueryRequest(BaseModel):
    """Request for temporal memory queries."""

    user_id: str
    since: datetime | None = None  # What changed since this time
    until: datetime | None = None
    kinds: list[str] | None = None
    operation: str | None = "changes"  # "changes", "timeline", "diff"


class TemporalQueryResponse(BaseModel):
    """Temporal query results showing memory evolution."""

    memories: list[MemoryResponse]
    created_count: int
    updated_count: int
    deleted_count: int
    period_start: datetime
    period_end: datetime


class SaveMemoryWithConfidenceRequest(BaseModel):
    """Save memory with explicit confidence scoring."""

    content: str
    kind: str
    scope: str = "user"
    duration: str
    user_id: str
    tags: list[str] | None = None
    importance: float | None = 1.0
    confidence: float | None = 1.0  # How confident are we in this memory
    source: str | None = "cursor"  # Where did this memory come from
    related_memory_ids: list[int] | None = None  # Link to related memories
    metadata: dict[str, Any] | None = None


# =============================================================================
# MCP Tool Argument Validation Models
# =============================================================================
# These models validate MCP tool arguments before handler dispatch.
# Each model corresponds to a tool's inputSchema from get_mcp_tools().
# Used in mcp_server.py handle_tool_call() for fail-fast validation.
# =============================================================================


class SaveMemoryArgs(BaseModel):
    """Validation model for save_memory tool arguments."""

    content: str
    kind: str  # Enum: preference, fact, context, error, success
    scope: str = "developer"  # Enum: developer, l-private, global
    duration: str  # Enum: short, medium, long
    user_id: str | None = None  # Injected server-side from caller identity
    tags: list[str] | None = None
    importance: float | None = 1.0  # Range: 0-1
    metadata: dict[str, Any] | None = None

    class Config:
        # Allow extra fields in metadata but validate known fields strictly
        extra = "forbid"


class SearchMemoryArgs(BaseModel):
    """Validation model for search_memory tool arguments."""

    query: str
    user_id: str | None = None  # Injected server-side from caller identity
    scopes: list[str] | None = None  # Enum: developer, l-private, global
    kinds: list[str] | None = None
    top_k: int | None = 5
    threshold: float | None = 0.7
    duration: str | None = "all"  # Enum: short, medium, long, all

    class Config:
        extra = "forbid"


class GetMemoryStatsArgs(BaseModel):
    """Validation model for get_memory_stats tool arguments."""

    user_id: str | None = None
    duration: str | None = "all"  # Enum: short, medium, long, all

    class Config:
        extra = "forbid"


class DeleteExpiredMemoriesArgs(BaseModel):
    """Validation model for delete_expired_memories tool arguments."""

    dry_run: bool | None = True

    class Config:
        extra = "forbid"


class CompoundMemoriesArgs(BaseModel):
    """Validation model for compound_memories tool arguments."""

    user_id: str | None = None  # Injected server-side from caller identity
    threshold: float | None = 0.92

    class Config:
        extra = "forbid"


class ApplyDecayArgs(BaseModel):
    """Validation model for apply_decay tool arguments."""

    dry_run: bool | None = True

    class Config:
        extra = "forbid"


class GetContextArgs(BaseModel):
    """Validation model for get_context tool arguments."""

    task_description: str
    user_id: str | None = None  # Injected server-side from caller identity
    top_k: int | None = 5
    include_recent: bool | None = True
    kinds: list[str] | None = None

    class Config:
        extra = "forbid"


class ExtractSessionLearningsArgs(BaseModel):
    """Validation model for extract_session_learnings tool arguments."""

    user_id: str | None = None  # Injected server-side from caller identity
    session_id: str
    session_summary: str
    key_decisions: list[str] | None = None
    errors_encountered: list[str] | None = None
    successes: list[str] | None = None

    class Config:
        extra = "forbid"


class GetProactiveSuggestionsArgs(BaseModel):
    """Validation model for get_proactive_suggestions tool arguments."""

    current_context: str
    user_id: str | None = None  # Injected server-side from caller identity
    include_error_fixes: bool | None = True
    include_preferences: bool | None = True
    top_k: int | None = 3

    class Config:
        extra = "forbid"


class QueryTemporalArgs(BaseModel):
    """Validation model for query_temporal tool arguments."""

    user_id: str | None = None  # Injected server-side from caller identity
    since: str | None = None  # ISO datetime string
    until: str | None = None  # ISO datetime string
    kinds: list[str] | None = None
    operation: str | None = "changes"  # Enum: changes, timeline, diff

    class Config:
        extra = "forbid"


class SaveMemoryWithConfidenceArgs(BaseModel):
    """Validation model for save_memory_with_confidence tool arguments."""

    content: str
    kind: str  # Enum: preference, fact, context, error, success, learning, decision
    scope: str = "developer"  # Enum: developer, l-private, global
    duration: str  # Enum: short, medium, long
    user_id: str | None = None  # Injected server-side from caller identity
    confidence: float | None = 1.0  # Range: 0-1
    source: str | None = "cursor"
    related_memory_ids: list[Any] | None = None  # UUIDs or legacy integer IDs
    tags: list[str] | None = None
    importance: float | None = 1.0  # Range: 0-1
    metadata: dict[str, Any] | None = None

    class Config:
        extra = "forbid"


# =============================================================================
# Graph (Neo4j) MCP Tool Argument Validation Models
# =============================================================================


class GraphQueryArgs(BaseModel):
    """Validation model for graph_query tool arguments."""

    query: str  # Cypher query string
    parameters: dict[str, Any] | None = None  # Query parameters

    class Config:
        extra = "forbid"


class GraphGetEntityArgs(BaseModel):
    """Validation model for graph_get_entity tool arguments."""

    entity_type: str  # Node label (Agent, Session, Memory, etc.)
    entity_id: str  # Entity identifier

    class Config:
        extra = "forbid"


class GraphGetContextArgs(BaseModel):
    """Validation model for graph_get_context tool arguments."""

    domain: str  # Domain name (memory, agents, tools, etc.)
    limit: int | None = 10  # Max results

    class Config:
        extra = "forbid"


# =============================================================================
# Graph Event (Neo4j Event nodes) MCP Tool Argument Validation Models
# =============================================================================


class GraphCreateEventArgs(BaseModel):
    """Validation model for graph_create_event tool arguments."""

    event_id: str  # Unique event identifier
    event_type: str  # Event type (e.g., 'user_action', 'agent_response')
    timestamp: str  # ISO timestamp
    properties: dict[str, Any] | None = None  # Event properties
    parent_event_id: str | None = None  # Optional parent for causality chain

    class Config:
        extra = "forbid"


class GraphGetEventTimelineArgs(BaseModel):
    """Validation model for graph_get_event_timeline tool arguments."""

    start_time: str | None = None  # ISO timestamp start (optional)
    end_time: str | None = None  # ISO timestamp end (optional)
    event_type: str | None = None  # Filter by event type (optional)
    limit: int | None = 100  # Maximum events to return

    class Config:
        extra = "forbid"


class GraphGetTemporalEventsArgs(BaseModel):
    """Validation model for graph_get_temporal_events tool arguments."""

    entity: str  # Entity ID to get events for
    start: str | None = None  # ISO timestamp start (optional)
    end: str | None = None  # ISO timestamp end (optional)

    class Config:
        extra = "forbid"


class GraphGetEventSequenceArgs(BaseModel):
    """Validation model for graph_get_event_sequence tool arguments."""

    entity: str  # Entity ID
    limit: int | None = 50  # Maximum events to return

    class Config:
        extra = "forbid"


# =============================================================================
# Cache (Redis) MCP Tool Argument Validation Models
# =============================================================================


class CacheGetArgs(BaseModel):
    """Validation model for cache_get tool arguments."""

    key: str  # Cache key

    class Config:
        extra = "forbid"


class CacheSetArgs(BaseModel):
    """Validation model for cache_set tool arguments."""

    key: str  # Cache key
    value: Any  # Value to store (will be JSON serialized)
    ttl: int | None = None  # TTL in seconds

    class Config:
        extra = "forbid"


class CacheGetSessionContextArgs(BaseModel):
    """Validation model for cache_get_session_context tool arguments."""

    session_id: str | None = None  # Session ID (defaults to daily session)

    class Config:
        extra = "forbid"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "data-models",
        "integration",
        "pydantic",
        "schema",
        "validation",
    ],
    "keywords": [
        "apply",
        "cache",
        "compound",
        "confidence",
        "decay",
        "delete",
        "entity",
        "expired",
    ],
    "business_value": "Provides models components including SaveMemoryRequest, MemoryResponse, SearchMemoryRequest",
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
