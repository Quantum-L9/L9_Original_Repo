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
    """Request model for saving a memory entry to the memory substrate.

    This model defines the structure for creating new memory entries with
    configurable scope, duration, and metadata.

    Attributes:
        content: The text content of the memory to store.
        kind: Category of memory (preference, fact, context, error, success).
        scope: Visibility scope (user, project, global). Defaults to "user".
        duration: Retention period (short, medium, long).
        user_id: Identifier of the user who owns this memory.
        tags: Optional list of tags for categorization.
        importance: Priority weight from 0.0 to 1.0. Defaults to 1.0.
        metadata: Optional dictionary for additional structured data.
    """

    content: str
    kind: str
    scope: str = "user"
    duration: str
    user_id: str
    tags: list[str] | None = None
    importance: float | None = 1.0
    metadata: dict[str, Any] | None = None


class MemoryResponse(BaseModel):
    """Response model representing a stored memory entry.

    Returned by memory retrieval and search operations, containing
    the full memory record with computed similarity scores.

    Attributes:
        id: Unique identifier for the memory entry.
        user_id: Identifier of the user who owns this memory.
        kind: Category of memory (preference, fact, context, error, success).
        content: The text content of the memory.
        importance: Priority weight from 0.0 to 1.0.
        tags: Optional list of tags for categorization.
        created_at: Timestamp when the memory was created.
        similarity: Optional cosine similarity score from vector search.
    """

    id: int
    user_id: str
    kind: str
    content: str
    importance: float
    tags: list[str] | None = None
    created_at: datetime
    similarity: float | None = None


class SearchMemoryRequest(BaseModel):
    """Request model for semantic memory search operations.

    Supports filtering by scope, kind, duration, and similarity threshold
    for targeted memory retrieval using vector embeddings.

    Attributes:
        query: Natural language search query for semantic matching.
        user_id: Identifier of the user whose memories to search.
        scopes: List of visibility scopes to search within.
        kinds: Optional filter for specific memory categories.
        top_k: Maximum number of results to return. Defaults to 5.
        threshold: Minimum similarity score (0.0-1.0). Defaults to 0.7.
        duration: Filter by retention period. Defaults to "all".
        track_access: Whether to update access timestamps. Defaults to False.
    """

    query: str
    user_id: str
    scopes: list[str] | None = ["user", "project", "global"]
    kinds: list[str] | None = None
    top_k: int | None = 5
    threshold: float | None = 0.7
    duration: str | None = "all"
    track_access: bool | None = False


class SearchMemoryResponse(BaseModel):
    """Response model for memory search operations.

    Contains the matched memories along with performance metrics
    for monitoring search latency.

    Attributes:
        results: List of matching memory entries with similarity scores.
        query_embedding_time_ms: Time to generate query embedding in milliseconds.
        search_time_ms: Time to execute vector search in milliseconds.
        total_results: Total number of matching results found.
    """

    results: list[MemoryResponse]
    query_embedding_time_ms: float
    search_time_ms: float
    total_results: int


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics aggregation.

    Provides counts and metrics across different memory durations
    and user populations.

    Attributes:
        short_term_count: Number of short-term memories.
        medium_term_count: Number of medium-term memories.
        long_term_count: Number of long-term memories.
        total_count: Total number of memories across all durations.
        unique_users: Count of distinct users with stored memories.
        avg_importance: Average importance score across all memories.
    """

    short_term_count: int
    medium_term_count: int
    long_term_count: int
    total_count: int
    unique_users: int
    avg_importance: float


class CompoundResult(BaseModel):
    """Response model for memory compounding operations.

    Reports the results of clustering and merging similar memories
    to reduce redundancy and boost importance of recurring patterns.

    Attributes:
        memories_analyzed: Total number of memories processed.
        clusters_found: Number of similar memory clusters identified.
        memories_merged: Number of redundant memories consolidated.
        importance_boosted: Number of memories with increased importance.
    """

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
    """Request model for extracting learnings from a completed session.

    Captures session outcomes including decisions made, errors encountered,
    and successes achieved for long-term memory storage.

    Attributes:
        user_id: Identifier of the user who completed the session.
        session_id: Unique identifier for the session.
        session_summary: High-level description of what occurred.
        key_decisions: Optional list of important decisions made.
        errors_encountered: Optional list of errors that occurred.
        successes: Optional list of successful outcomes achieved.
    """

    user_id: str
    session_id: str
    session_summary: str  # What happened this session
    key_decisions: list[str] | None = None
    errors_encountered: list[str] | None = None
    successes: list[str] | None = None


class SessionLearningResponse(BaseModel):
    """Response model for session learning extraction.

    Reports the memories created from session analysis including
    their IDs and categorization.

    Attributes:
        learnings_stored: Number of learning memories created.
        memory_ids: List of IDs for the created memory entries.
        kinds_created: List of memory kinds that were generated.
    """

    learnings_stored: int
    memory_ids: list[int]
    kinds_created: list[str]


class ProactiveRecallRequest(BaseModel):
    """Request model for proactive memory suggestions.

    Triggers pattern-based memory retrieval to surface relevant
    past experiences, error fixes, and user preferences.

    Attributes:
        current_context: Description of the user's current task or situation.
        user_id: Identifier of the user for personalized suggestions.
        include_error_fixes: Whether to include error-fix pairs. Defaults to True.
        include_preferences: Whether to include user preferences. Defaults to True.
        top_k: Maximum suggestions to return. Defaults to 3.
    """

    current_context: str  # What user is currently working on
    user_id: str
    include_error_fixes: bool | None = True
    include_preferences: bool | None = True
    top_k: int | None = 3


class ProactiveRecallResponse(BaseModel):
    """Response model for proactive memory suggestions.

    Contains contextually relevant memories, error-fix pairs,
    and user preferences surfaced from the memory substrate.

    Attributes:
        suggestions: List of contextually relevant memory entries.
        error_fix_pairs: List of error-fix mappings with confidence scores.
        relevant_preferences: List of applicable user preference memories.
        recall_time_ms: Time to retrieve suggestions in milliseconds.
    """

    suggestions: list[MemoryResponse]
    error_fix_pairs: list[dict[str, Any]]  # {error: str, fix: str, confidence: float}
    relevant_preferences: list[MemoryResponse]
    recall_time_ms: float


class TemporalQueryRequest(BaseModel):
    """Request model for time-based memory queries.

    Enables querying memory changes, timelines, and diffs
    within specified time windows.

    Attributes:
        user_id: Identifier of the user whose memories to query.
        since: Optional start datetime for the query window.
        until: Optional end datetime for the query window.
        kinds: Optional filter for specific memory categories.
        operation: Query type (changes, timeline, diff). Defaults to "changes".
    """

    user_id: str
    since: datetime | None = None  # What changed since this time
    until: datetime | None = None
    kinds: list[str] | None = None
    operation: str | None = "changes"  # "changes", "timeline", "diff"


class TemporalQueryResponse(BaseModel):
    """Response model for temporal memory queries.

    Shows memory evolution over time including creation,
    update, and deletion counts within the query period.

    Attributes:
        memories: List of memories matching the temporal query.
        created_count: Number of memories created in the period.
        updated_count: Number of memories updated in the period.
        deleted_count: Number of memories deleted in the period.
        period_start: Start datetime of the query period.
        period_end: End datetime of the query period.
    """

    memories: list[MemoryResponse]
    created_count: int
    updated_count: int
    deleted_count: int
    period_start: datetime
    period_end: datetime


class SaveMemoryWithConfidenceRequest(BaseModel):
    """Request model for saving memory with confidence metadata.

    Extended save request that includes confidence scoring,
    source tracking, and memory relationship linking.

    Attributes:
        content: The text content of the memory to store.
        kind: Category of memory (preference, fact, context, error, success).
        scope: Visibility scope (user, project, global). Defaults to "user".
        duration: Retention period (short, medium, long).
        user_id: Identifier of the user who owns this memory.
        tags: Optional list of tags for categorization.
        importance: Priority weight from 0.0 to 1.0. Defaults to 1.0.
        confidence: Certainty score from 0.0 to 1.0. Defaults to 1.0.
        source: Origin of the memory (cursor, api, etc.). Defaults to "cursor".
        related_memory_ids: Optional list of linked memory IDs.
        metadata: Optional dictionary for additional structured data.
    """

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
    """Validation model for save_memory MCP tool arguments.

    Validates and normalizes arguments before dispatching to the save_memory
    handler. Enforces strict field validation with no extra fields allowed.

    Attributes:
        content: The text content of the memory to store.
        kind: Memory category (preference, fact, context, error, success).
        scope: Visibility scope (developer, l-private, global).
        duration: Retention period (short, medium, long).
        user_id: User identifier, injected server-side from caller identity.
        tags: Optional list of tags for categorization.
        importance: Priority weight from 0.0 to 1.0.
        metadata: Optional dictionary for additional structured data.
    """

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
    """Validation model for search_memory MCP tool arguments.

    Validates semantic search parameters before dispatching to the
    search_memory handler. Supports scope and kind filtering.

    Attributes:
        query: Natural language search query for semantic matching.
        user_id: User identifier, injected server-side from caller identity.
        scopes: List of visibility scopes to search (developer, l-private, global).
        kinds: Optional filter for specific memory categories.
        top_k: Maximum number of results to return.
        threshold: Minimum similarity score (0.0-1.0).
        duration: Filter by retention period (short, medium, long, all).
    """

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
    """Validation model for get_memory_stats MCP tool arguments.

    Validates parameters for retrieving memory statistics aggregations.

    Attributes:
        user_id: Optional user identifier to filter statistics.
        duration: Filter by retention period (short, medium, long, all).
    """

    user_id: str | None = None
    duration: str | None = "all"  # Enum: short, medium, long, all

    class Config:
        extra = "forbid"


class DeleteExpiredMemoriesArgs(BaseModel):
    """Validation model for delete_expired_memories MCP tool arguments.

    Validates parameters for the memory cleanup operation that removes
    expired entries based on their retention duration.

    Attributes:
        dry_run: If True, report deletions without executing. Defaults to True.
    """

    dry_run: bool | None = True

    class Config:
        extra = "forbid"


class CompoundMemoriesArgs(BaseModel):
    """Validation model for compound_memories MCP tool arguments.

    Validates parameters for the memory compounding operation that
    clusters and merges similar memories to reduce redundancy.

    Attributes:
        user_id: User identifier, injected server-side from caller identity.
        threshold: Similarity threshold for clustering (0.0-1.0).
    """

    user_id: str | None = None  # Injected server-side from caller identity
    threshold: float | None = 0.92

    class Config:
        extra = "forbid"


class ApplyDecayArgs(BaseModel):
    """Validation model for apply_decay MCP tool arguments.

    Validates parameters for the importance decay operation that
    reduces memory importance scores over time based on access patterns.

    Attributes:
        dry_run: If True, report decay effects without applying. Defaults to True.
    """

    dry_run: bool | None = True

    class Config:
        extra = "forbid"


class GetContextArgs(BaseModel):
    """Validation model for get_context MCP tool arguments.

    Validates parameters for context injection that retrieves relevant
    memories to augment the system prompt before task execution.

    Attributes:
        task_description: Description of the task requiring context.
        user_id: User identifier, injected server-side from caller identity.
        top_k: Maximum number of context memories to retrieve.
        include_recent: Whether to include recent (24h) context.
        kinds: Optional filter for specific memory categories.
    """

    task_description: str
    user_id: str | None = None  # Injected server-side from caller identity
    top_k: int | None = 5
    include_recent: bool | None = True
    kinds: list[str] | None = None

    class Config:
        extra = "forbid"


class ExtractSessionLearningsArgs(BaseModel):
    """Validation model for extract_session_learnings MCP tool arguments.

    Validates parameters for extracting and storing learnings from
    a completed session including decisions, errors, and successes.

    Attributes:
        user_id: User identifier, injected server-side from caller identity.
        session_id: Unique identifier for the session.
        session_summary: High-level description of what occurred.
        key_decisions: Optional list of important decisions made.
        errors_encountered: Optional list of errors that occurred.
        successes: Optional list of successful outcomes achieved.
    """

    user_id: str | None = None  # Injected server-side from caller identity
    session_id: str
    session_summary: str
    key_decisions: list[str] | None = None
    errors_encountered: list[str] | None = None
    successes: list[str] | None = None

    class Config:
        extra = "forbid"


class GetProactiveSuggestionsArgs(BaseModel):
    """Validation model for get_proactive_suggestions MCP tool arguments.

    Validates parameters for proactive memory suggestions that surface
    relevant past experiences based on the current context.

    Attributes:
        current_context: Description of the user's current task or situation.
        user_id: User identifier, injected server-side from caller identity.
        include_error_fixes: Whether to include error-fix pairs.
        include_preferences: Whether to include user preferences.
        top_k: Maximum number of suggestions to return.
    """

    current_context: str
    user_id: str | None = None  # Injected server-side from caller identity
    include_error_fixes: bool | None = True
    include_preferences: bool | None = True
    top_k: int | None = 3

    class Config:
        extra = "forbid"


class QueryTemporalArgs(BaseModel):
    """Validation model for query_temporal MCP tool arguments.

    Validates parameters for time-based memory queries that show
    memory evolution within specified time windows.

    Attributes:
        user_id: User identifier, injected server-side from caller identity.
        since: Optional ISO datetime string for query window start.
        until: Optional ISO datetime string for query window end.
        kinds: Optional filter for specific memory categories.
        operation: Query type (changes, timeline, diff).
    """

    user_id: str | None = None  # Injected server-side from caller identity
    since: str | None = None  # ISO datetime string
    until: str | None = None  # ISO datetime string
    kinds: list[str] | None = None
    operation: str | None = "changes"  # Enum: changes, timeline, diff

    class Config:
        extra = "forbid"


class SaveMemoryWithConfidenceArgs(BaseModel):
    """Validation model for save_memory_with_confidence MCP tool arguments.

    Validates extended save parameters including confidence scoring,
    source tracking, and memory relationship linking.

    Attributes:
        content: The text content of the memory to store.
        kind: Memory category (preference, fact, context, error, success, learning, decision).
        scope: Visibility scope (developer, l-private, global).
        duration: Retention period (short, medium, long).
        user_id: User identifier, injected server-side from caller identity.
        confidence: Certainty score from 0.0 to 1.0.
        source: Origin of the memory (cursor, api, etc.).
        related_memory_ids: Optional list of linked memory IDs (UUIDs or integers).
        tags: Optional list of tags for categorization.
        importance: Priority weight from 0.0 to 1.0.
        metadata: Optional dictionary for additional structured data.
    """

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
    """Validation model for graph_query MCP tool arguments.

    Validates parameters for executing Cypher queries against the
    Neo4j knowledge graph.

    Attributes:
        query: Cypher query string to execute.
        parameters: Optional dictionary of query parameters for parameterized queries.
    """

    query: str  # Cypher query string
    parameters: dict[str, Any] | None = None  # Query parameters

    class Config:
        extra = "forbid"


class GraphGetEntityArgs(BaseModel):
    """Validation model for graph_get_entity MCP tool arguments.

    Validates parameters for retrieving a specific entity node
    from the Neo4j knowledge graph.

    Attributes:
        entity_type: Node label (Agent, Session, Memory, Tool, etc.).
        entity_id: Unique identifier for the entity.
    """

    entity_type: str  # Node label (Agent, Session, Memory, etc.)
    entity_id: str  # Entity identifier

    class Config:
        extra = "forbid"


class GraphGetContextArgs(BaseModel):
    """Validation model for graph_get_context MCP tool arguments.

    Validates parameters for retrieving contextual information
    from a specific domain in the knowledge graph.

    Attributes:
        domain: Domain name to query (memory, agents, tools, etc.).
        limit: Maximum number of results to return.
    """

    domain: str  # Domain name (memory, agents, tools, etc.)
    limit: int | None = 10  # Max results

    class Config:
        extra = "forbid"


# =============================================================================
# Cache (Redis) MCP Tool Argument Validation Models
# =============================================================================


class CacheGetArgs(BaseModel):
    """Validation model for cache_get MCP tool arguments.

    Validates parameters for retrieving a value from the Redis cache.

    Attributes:
        key: Cache key to retrieve.
    """

    key: str  # Cache key

    class Config:
        extra = "forbid"


class CacheSetArgs(BaseModel):
    """Validation model for cache_set MCP tool arguments.

    Validates parameters for storing a value in the Redis cache
    with optional time-to-live expiration.

    Attributes:
        key: Cache key for storage.
        value: Value to store (will be JSON serialized).
        ttl: Optional time-to-live in seconds before expiration.
    """

    key: str  # Cache key
    value: Any  # Value to store (will be JSON serialized)
    ttl: int | None = None  # TTL in seconds

    class Config:
        extra = "forbid"


class CacheGetSessionContextArgs(BaseModel):
    """Validation model for cache_get_session_context MCP tool arguments.

    Validates parameters for retrieving session context from the cache,
    which stores recent conversation and task state.

    Attributes:
        session_id: Session identifier. Defaults to daily session if not provided.
    """

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
