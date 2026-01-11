"""
Request/response models.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class SaveMemoryRequest(BaseModel):
    content: str
    kind: str
    scope: str = "user"
    duration: str
    user_id: str
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: int
    user_id: str
    kind: str
    content: str
    importance: float
    tags: Optional[List[str]] = None
    created_at: datetime
    similarity: Optional[float] = None


class SearchMemoryRequest(BaseModel):
    query: str
    user_id: str
    scopes: Optional[List[str]] = ["user", "project", "global"]
    kinds: Optional[List[str]] = None
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.7
    duration: Optional[str] = "all"


class SearchMemoryResponse(BaseModel):
    results: List[MemoryResponse]
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
    top_k: Optional[int] = 5
    include_recent: Optional[bool] = True  # Include last 24h context
    kinds: Optional[List[str]] = None  # Filter by memory kinds


class ContextInjectionResponse(BaseModel):
    """Context memories to inject into system prompt."""
    memories: List[MemoryResponse]
    recent_context: List[MemoryResponse]
    total_injected: int
    retrieval_time_ms: float


class SessionLearningRequest(BaseModel):
    """Request to extract learnings from a session."""
    user_id: str
    session_id: str
    session_summary: str  # What happened this session
    key_decisions: Optional[List[str]] = None
    errors_encountered: Optional[List[str]] = None
    successes: Optional[List[str]] = None


class SessionLearningResponse(BaseModel):
    """Learnings extracted and stored from session."""
    learnings_stored: int
    memory_ids: List[int]
    kinds_created: List[str]


class ProactiveRecallRequest(BaseModel):
    """Request for proactive memory suggestions based on patterns."""
    current_context: str  # What user is currently working on
    user_id: str
    include_error_fixes: Optional[bool] = True
    include_preferences: Optional[bool] = True
    top_k: Optional[int] = 3


class ProactiveRecallResponse(BaseModel):
    """Proactive suggestions surfaced from memory."""
    suggestions: List[MemoryResponse]
    error_fix_pairs: List[Dict[str, Any]]  # {error: str, fix: str, confidence: float}
    relevant_preferences: List[MemoryResponse]
    recall_time_ms: float


class TemporalQueryRequest(BaseModel):
    """Request for temporal memory queries."""
    user_id: str
    since: Optional[datetime] = None  # What changed since this time
    until: Optional[datetime] = None
    kinds: Optional[List[str]] = None
    operation: Optional[str] = "changes"  # "changes", "timeline", "diff"


class TemporalQueryResponse(BaseModel):
    """Temporal query results showing memory evolution."""
    memories: List[MemoryResponse]
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
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0
    confidence: Optional[float] = 1.0  # How confident are we in this memory
    source: Optional[str] = "cursor"  # Where did this memory come from
    related_memory_ids: Optional[List[int]] = None  # Link to related memories
    metadata: Optional[Dict[str, Any]] = None


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
    user_id: str
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0  # Range: 0-1
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        # Allow extra fields in metadata but validate known fields strictly
        extra = "forbid"


class SearchMemoryArgs(BaseModel):
    """Validation model for search_memory tool arguments."""
    query: str
    user_id: str
    scopes: Optional[List[str]] = None  # Enum: developer, l-private, global
    kinds: Optional[List[str]] = None
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.7
    duration: Optional[str] = "all"  # Enum: short, medium, long, all

    class Config:
        extra = "forbid"


class GetMemoryStatsArgs(BaseModel):
    """Validation model for get_memory_stats tool arguments."""
    user_id: Optional[str] = None
    duration: Optional[str] = "all"  # Enum: short, medium, long, all

    class Config:
        extra = "forbid"


class DeleteExpiredMemoriesArgs(BaseModel):
    """Validation model for delete_expired_memories tool arguments."""
    dry_run: Optional[bool] = True

    class Config:
        extra = "forbid"


class CompoundMemoriesArgs(BaseModel):
    """Validation model for compound_memories tool arguments."""
    user_id: str
    threshold: Optional[float] = 0.92

    class Config:
        extra = "forbid"


class ApplyDecayArgs(BaseModel):
    """Validation model for apply_decay tool arguments."""
    dry_run: Optional[bool] = True

    class Config:
        extra = "forbid"


class GetContextArgs(BaseModel):
    """Validation model for get_context tool arguments."""
    task_description: str
    user_id: str
    top_k: Optional[int] = 5
    include_recent: Optional[bool] = True
    kinds: Optional[List[str]] = None

    class Config:
        extra = "forbid"


class ExtractSessionLearningsArgs(BaseModel):
    """Validation model for extract_session_learnings tool arguments."""
    user_id: str
    session_id: str
    session_summary: str
    key_decisions: Optional[List[str]] = None
    errors_encountered: Optional[List[str]] = None
    successes: Optional[List[str]] = None

    class Config:
        extra = "forbid"


class GetProactiveSuggestionsArgs(BaseModel):
    """Validation model for get_proactive_suggestions tool arguments."""
    current_context: str
    user_id: str
    include_error_fixes: Optional[bool] = True
    include_preferences: Optional[bool] = True
    top_k: Optional[int] = 3

    class Config:
        extra = "forbid"


class QueryTemporalArgs(BaseModel):
    """Validation model for query_temporal tool arguments."""
    user_id: str
    since: Optional[str] = None  # ISO datetime string
    until: Optional[str] = None  # ISO datetime string
    kinds: Optional[List[str]] = None
    operation: Optional[str] = "changes"  # Enum: changes, timeline, diff

    class Config:
        extra = "forbid"


class SaveMemoryWithConfidenceArgs(BaseModel):
    """Validation model for save_memory_with_confidence tool arguments."""
    content: str
    kind: str  # Enum: preference, fact, context, error, success, learning, decision
    scope: str = "developer"  # Enum: developer, l-private, global
    duration: str  # Enum: short, medium, long
    user_id: str
    confidence: Optional[float] = 1.0  # Range: 0-1
    source: Optional[str] = "cursor"
    related_memory_ids: Optional[List[Any]] = None  # UUIDs or legacy integer IDs
    tags: Optional[List[str]] = None
    importance: Optional[float] = 1.0  # Range: 0-1
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"
