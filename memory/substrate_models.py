"""
L9 Memory Substrate - Database DTOs and Memory-Specific Models
Version: 2.0.0

This module contains:
- Database row DTOs (PacketStoreRow, KnowledgeFactRow, etc.)
- Memory-specific models (StructuredReasoningBlock, SubstrateState)
- Knowledge extraction models (KnowledgeFact, ExtractedInsight)
- Enrichment pipeline models (EnrichmentResult)
- Memory segment enum (MemorySegment)

For PacketEnvelope and related schemas, use:
    from core.schemas import PacketEnvelope, PacketEnvelopeIn

Changelog v2.0.0:
- Removed duplicate PacketEnvelope classes (now in core.schemas.packet_envelope_v2)
- Removed deprecation warning (this module is NOT deprecated)
- Clarified purpose: DB DTOs and memory-specific models only

Changelog v1.1.1:
- Added frozen=True to enforce immutability (GMP#1)

Changelog v1.1.0:
- Added PacketLineage model for DAG-style packet relationships
- Added thread_id, lineage, tags, ttl to PacketEnvelope
- Updated PacketEnvelopeIn with new fields
- Updated PacketStoreRow with new DB columns
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Memory Segment Enum
# =============================================================================


class MemorySegment(str, Enum):
    """
    L9 memory organization - 4 canonical segments.

    Each segment represents a distinct type of memory with different
    retention, access patterns, and governance rules.
    """

    GOVERNANCE_META = "governance_meta"
    """Authority, meta-prompts, kernel definitions (immutable)."""

    PROJECT_HISTORY = "project_history"
    """Plans, decisions, outcomes, GMP reports."""

    TOOL_AUDIT = "tool_audit"
    """Tool invocation audit trail - every tool call logged."""

    SESSION_CONTEXT = "session_context"
    """Short-term working memory, conversation context (TTL-based)."""


# =============================================================================
# Structured Reasoning Block Models
# =============================================================================


class StructuredReasoningBlock(BaseModel):
    """
    Structured reasoning block for capturing inference traces.

    Attached to packets that go through reasoning_node in the DAG.
    """

    block_id: UUID = Field(
        default_factory=uuid4, description="UUID for this reasoning block"
    )
    packet_id: UUID = Field(..., description="Associated packet ID")
    extracted_features: dict[str, Any] = Field(
        default_factory=dict, description="Features extracted from payload"
    )
    inference_steps: list[dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step inference"
    )
    reasoning_tokens: list[str] = Field(
        default_factory=list, description="Reasoning token sequence"
    )
    decision_tokens: list[str] = Field(
        default_factory=list, description="Decision token sequence"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Confidence by step/decision"
    )
    memory_write_ops: list[dict[str, Any]] = Field(
        default_factory=list, description="Memory operations to perform"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# DAG State Models (for LangGraph)
# =============================================================================


class SubstrateState(BaseModel):
    """
    State object passed through the LangGraph DAG.

    Contains the packet being processed and accumulated results.
    
    Note: References PacketEnvelope from core.schemas.packet_envelope_v2
    """

    envelope: Any  # PacketEnvelope - imported at runtime to avoid circular imports
    reasoning_block: Optional[StructuredReasoningBlock] = None
    written_tables: list[str] = Field(default_factory=list)
    embedding_generated: bool = False
    checkpoint_saved: bool = False
    errors: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Database Row DTOs
# =============================================================================


class AgentMemoryEventRow(BaseModel):
    """DTO for agent_memory_events table."""

    event_id: UUID
    agent_id: str
    timestamp: datetime
    packet_id: Optional[UUID]
    event_type: str
    content: dict[str, Any]


class SemanticMemoryRow(BaseModel):
    """DTO for semantic_memory table."""

    embedding_id: UUID
    agent_id: Optional[str]
    vector: list[float]  # 1536 dimensions
    payload: dict[str, Any]
    created_at: datetime


class ReasoningTraceRow(BaseModel):
    """DTO for reasoning_traces table."""

    trace_id: UUID
    agent_id: str
    packet_id: Optional[UUID]
    steps: Optional[dict[str, Any]]
    extracted_features: Optional[dict[str, Any]]
    inference_steps: Optional[list[dict[str, Any]]]
    reasoning_tokens: Optional[list[str]]
    decision_tokens: Optional[list[str]]
    confidence_scores: Optional[dict[str, float]]
    created_at: datetime


class PacketStoreRow(BaseModel):
    """DTO for packet_store table (v2.0 - all columns from migrations 0001, 0002, 0008)."""

    # Core fields (migration 0001)
    packet_id: UUID
    packet_type: str
    envelope: dict[str, Any]
    timestamp: datetime
    routing: Optional[dict[str, Any]] = None
    provenance: Optional[dict[str, Any]] = None

    # Threading & lineage (migration 0002)
    thread_id: Optional[UUID] = None
    parent_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    ttl: Optional[datetime] = None

    # 10X Enhancements (migration 0008)
    scope: Optional[str] = "shared"
    importance_score: Optional[float] = 0.5
    access_count: Optional[int] = 0
    last_accessed: Optional[datetime] = None
    confidence_updated_at: Optional[datetime] = None
    contradiction_count: Optional[int] = 0
    chunk_count: Optional[int] = 1
    is_chunked: Optional[bool] = False
    content_hash: Optional[str] = None
    processing_status: Optional[str] = "complete"

    # Multi-tenant identity (migration 0008)
    tenant_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None

    # Tracing (migration 0008)
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


class GraphCheckpointRow(BaseModel):
    """DTO for graph_checkpoints table."""

    checkpoint_id: UUID
    agent_id: str
    graph_state: dict[str, Any]
    updated_at: datetime
    reason: Optional[str] = None  # Added in migration 0014, optional for backward compat
    checkpoint_number: Optional[int] = None  # Added in migration 0014


# =============================================================================
# Knowledge Facts Models (v1.1.0+)
# =============================================================================


class KnowledgeFact(BaseModel):
    """
    A knowledge fact extracted from packet processing.

    Represents subject-predicate-object triples with confidence
    for populating the knowledge graph / world model.
    """

    fact_id: UUID = Field(default_factory=uuid4, description="UUID for this fact")
    subject: str = Field(..., description="Entity or concept being described")
    predicate: str = Field(..., description="Relationship or attribute type")
    object: Any = Field(..., description="Value, entity, or structured data")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Extraction confidence"
    )
    source_packet: Optional[UUID] = Field(None, description="Originating packet ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeFactRow(BaseModel):
    """DTO for knowledge_facts table."""

    fact_id: UUID
    subject: str
    predicate: str
    object: Any
    confidence: Optional[float]
    source_packet: Optional[UUID]
    created_at: datetime


class ExtractedInsight(BaseModel):
    """
    An insight extracted from packet reasoning.

    Higher-level abstraction than KnowledgeFact - represents
    conclusions, patterns, or actionable information.
    """

    insight_id: UUID = Field(default_factory=uuid4)
    insight_type: str = Field(
        ..., description="Type: 'pattern', 'conclusion', 'recommendation', 'anomaly'"
    )
    content: str = Field(..., description="Natural language insight description")
    entities: list[str] = Field(default_factory=list, description="Referenced entities")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    source_packet: Optional[UUID] = None
    facts: list[KnowledgeFact] = Field(
        default_factory=list, description="Supporting facts"
    )
    trigger_world_model: bool = Field(
        default=False, description="Whether to propagate to world model"
    )


# =============================================================================
# Enrichment Result Model (v2.1.0 - GMP-67 Unified Pipeline)
# =============================================================================


class EnrichmentResult(BaseModel):
    """
    Result of SubstrateDAG.enrich() execution (v2.1.0 - GMP-67).
    
    Returned by DAG enrichment when running in enrichment-only mode
    (after core writes have been completed by IngestionPipeline).
    
    Contains extracted facts, insights, reasoning traces, and metrics.
    """
    
    packet_id: UUID = Field(..., description="Source packet that was enriched")
    
    # Extracted data
    facts: list[KnowledgeFact] = Field(
        default_factory=list, description="Extracted knowledge facts (SPO triples)"
    )
    insights: list[ExtractedInsight] = Field(
        default_factory=list, description="Higher-level extracted insights"
    )
    reasoning_trace: Optional[StructuredReasoningBlock] = Field(
        None, description="Reasoning trace if generated during enrichment"
    )
    
    # Persistence metrics
    facts_inserted: int = Field(
        default=0, description="Number of facts persisted to knowledge_facts table"
    )
    world_model_triggered: bool = Field(
        default=False, description="Whether world model update was triggered"
    )
    
    # Timing metrics
    enrichment_duration_ms: float = Field(
        default=0.0, description="Total enrichment execution time in milliseconds"
    )
