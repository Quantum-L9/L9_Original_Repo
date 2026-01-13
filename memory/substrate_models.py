"""
L9 Memory Substrate - Pydantic Models
Version: 1.1.1 (DEPRECATED)

⚠️  DEPRECATION NOTICE ⚠️
This module is DEPRECATED as of 2026-01-05.
Use `core.schemas.packet_envelope_v2` for the canonical PacketEnvelope.

Sunset timeline:
- 2026-01-05: Deprecation announced
- 2026-02-20: Sunset warning (45 days)
- 2026-03-22: Write block (75 days)
- 2026-04-05: Read block (90 days) - migration required

Migration:
    # OLD (deprecated)
    from memory.substrate_models import PacketEnvelope
    
    # NEW (canonical)
    from core.schemas.packet_envelope_v2 import PacketEnvelope

Changelog v1.1.1:
- Added frozen=True to enforce immutability (GMP#1)
- DEPRECATED in favor of core.schemas.packet_envelope_v2

Changelog v1.1.0:
- Added PacketLineage model for DAG-style packet relationships
- Added thread_id, lineage, tags, ttl to PacketEnvelope
- Updated PacketEnvelopeIn with new fields
- Updated PacketStoreRow with new DB columns
"""

import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Emit deprecation warning on import
warnings.warn(
    "memory.substrate_models is deprecated. "
    "Use core.schemas.packet_envelope_v2 instead. "
    "Sunset date: 2026-04-05",
    DeprecationWarning,
    stacklevel=2,
)


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
# PacketEnvelope Models
# =============================================================================


class PacketConfidence(BaseModel):
    """Confidence score and rationale for a packet."""

    score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    rationale: Optional[str] = Field(
        None, description="Explanation of confidence level"
    )

    model_config = {"frozen": True}


class PacketProvenance(BaseModel):
    """Provenance information for packet traceability."""

    parent_packet: Optional[UUID] = Field(
        None, description="Parent packet ID if derived"
    )
    source: Optional[str] = Field(None, description="Source system or agent")
    tool: Optional[str] = Field(None, description="Tool that generated this packet")

    model_config = {"frozen": True}


class PacketLineage(BaseModel):
    """
    Lineage information for packet genealogy tracking (v1.1.0).

    Enables tracing the full derivation path of a packet through
    the system, supporting multi-parent DAG relationships.
    """

    parent_ids: list[UUID] = Field(
        default_factory=list, description="Parent packet IDs (multi-parent DAG)"
    )
    derivation_type: Optional[str] = Field(
        None, description="How derived: 'split', 'merge', 'transform', 'inference', 'mutation'"
    )
    generation: int = Field(default=0, description="Generation number in lineage chain")
    root_packet_id: Optional[UUID] = Field(
        None, description="Original root packet if known"
    )

    model_config = {"frozen": True}


class PacketMetadata(BaseModel):
    """Metadata attached to a packet envelope."""

    schema_version: Optional[str] = Field("1.1.1", description="Schema version")
    reasoning_mode: Optional[str] = Field(None, description="Reasoning mode used")
    agent: Optional[str] = Field(None, description="Agent identifier")
    domain: Optional[str] = Field("l9", description="Domain context")

    model_config = {"frozen": True, "extra": "allow"}


class PacketEnvelope(BaseModel):
    """
    Canonical envelope for substrate writes and reasoning traces.

    This is the core data structure for all agent events, memory writes,
    and reasoning traces flowing through the memory substrate.

    IMMUTABLE CONTRACT: PacketEnvelope is frozen once created. Any
    modifications must use with_mutation() which creates a new packet
    with proper lineage chain linking to the parent.

    v1.1.0: Added thread_id, lineage, tags, ttl for enhanced
    threading, DAG-style lineage, labeling, and memory expiration.
    v1.1.1: Added model_config for immutability enforcement (frozen=True).
    """

    packet_id: UUID = Field(default_factory=uuid4, description="UUID for this packet")
    packet_type: str = Field(
        ...,
        description="Type: 'event', 'memory_write', 'reasoning_trace', 'insight', etc.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="ISO timestamp"
    )
    payload: dict[str, Any] = Field(
        ..., description="JSON payload to persist or reason over"
    )
    metadata: Optional[PacketMetadata] = Field(default_factory=PacketMetadata)
    provenance: Optional[PacketProvenance] = Field(None)
    confidence: Optional[PacketConfidence] = Field(None)
    reasoning_block: Optional[dict[str, Any]] = Field(
        None, description="Optional StructuredReasoningBlock inline"
    )

    # v1.1.0 additions (backward compatible - all optional)
    thread_id: Optional[UUID] = Field(
        None, description="Logical conversation/task thread identifier"
    )
    lineage: Optional[PacketLineage] = Field(
        None, description="Lineage metadata for DAG-style derivation tracking"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Lightweight labels for filtering and retrieval",
    )
    ttl: Optional[datetime] = Field(
        None, description="Optional expiry timestamp for memory hygiene/GC"
    )

    # v1.1.1: IMMUTABILITY ENFORCEMENT (matches core/schemas/packet_envelope.py)
    model_config = {
        "frozen": True,  # IMMUTABILITY ENFORCED - packets cannot be mutated
        "validate_assignment": True,
        "extra": "forbid",
    }

    def with_mutation(self, **updates) -> "PacketEnvelope":
        """
        Create a new PacketEnvelope with updates, linking to this as parent.

        This is the ONLY way to "modify" a packet (immutability preserved).
        Creates proper lineage chain for audit trail and DAG relationships.

        Args:
            **updates: Fields to update in the new packet

        Returns:
            New PacketEnvelope with:
            - New packet_id
            - Updated timestamp
            - Lineage linking to this packet as parent
            - All other fields preserved or updated
        """
        # Build lineage chain
        current_generation = self.lineage.generation if self.lineage else 0
        root_id = (
            self.lineage.root_packet_id
            if self.lineage and self.lineage.root_packet_id
            else self.packet_id
        )

        new_lineage = PacketLineage(
            parent_ids=[self.packet_id],
            derivation_type="mutation",
            generation=current_generation + 1,
            root_packet_id=root_id,
        )

        # Create new packet with updates
        return self.model_copy(
            update={
                "packet_id": uuid4(),
                "timestamp": datetime.utcnow(),
                "lineage": new_lineage,
                **updates,
            }
        )


class PacketEnvelopeIn(BaseModel):
    """
    Input model for packet submission (allows partial fields).
    packet_id and timestamp are auto-generated if not provided.

    v1.1.0: Added thread_id, lineage, tags, ttl support.
    """

    packet_id: Optional[UUID] = Field(
        None, description="UUID for this packet (auto-generated if omitted)"
    )
    packet_type: str = Field(
        ...,
        description="Type: 'event', 'memory_write', 'reasoning_trace', 'insight', etc.",
    )
    timestamp: Optional[datetime] = Field(
        None, description="ISO timestamp (auto-generated if omitted)"
    )
    payload: dict[str, Any] = Field(
        ..., description="JSON payload to persist or reason over"
    )
    metadata: Optional[PacketMetadata] = Field(None)
    provenance: Optional[PacketProvenance] = Field(None)
    confidence: Optional[PacketConfidence] = Field(None)
    reasoning_block: Optional[dict[str, Any]] = Field(None)

    # v1.1.0 additions
    thread_id: Optional[UUID] = Field(
        None, description="Thread UUID for conversation/session linking"
    )
    lineage: Optional[PacketLineage] = Field(
        None, description="Packet derivation lineage"
    )
    tags: Optional[list[str]] = Field(None, description="Flexible tags for filtering")
    ttl: Optional[datetime] = Field(None, description="Optional expiration timestamp")

    def to_envelope(self) -> PacketEnvelope:
        """Convert input to full PacketEnvelope with defaults."""
        return PacketEnvelope(
            packet_id=self.packet_id or uuid4(),
            packet_type=self.packet_type,
            timestamp=self.timestamp or datetime.utcnow(),
            payload=self.payload,
            metadata=self.metadata or PacketMetadata(),
            provenance=self.provenance,
            confidence=self.confidence,
            reasoning_block=self.reasoning_block,
            # v1.1.0 fields
            thread_id=self.thread_id,
            lineage=self.lineage,
            tags=self.tags or [],
            ttl=self.ttl,
        )


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
# Semantic Search Models
# =============================================================================


class SemanticSearchRequest(BaseModel):
    """Request to search semantic memory."""

    query: str = Field(..., min_length=1, description="Natural language query")
    top_k: int = Field(10, ge=1, le=100, description="Number of neighbors to return")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score threshold")


class SemanticHit(BaseModel):
    """Single semantic search result."""

    embedding_id: UUID = Field(..., description="Embedding record ID")
    score: float = Field(..., description="Similarity score")
    payload: dict[str, Any] = Field(..., description="Stored payload")


class SemanticSearchResult(BaseModel):
    """Top-k semantic hits."""

    query: str = Field(..., description="Original query")
    hits: list[SemanticHit] = Field(
        default_factory=list, description="List of matching results"
    )


# =============================================================================
# Packet Write Response Models
# =============================================================================


class PacketWriteResult(BaseModel):
    """Result of writing a PacketEnvelope."""

    packet_id: UUID = Field(..., description="Echoed packet ID")
    written_tables: list[str] = Field(
        default_factory=list, description="Tables updated"
    )
    status: str = Field("ok", description="'ok' or 'error'")
    error_message: Optional[str] = Field(
        None, description="Error details if status='error'"
    )


# =============================================================================
# DAG State Models (for LangGraph)
# =============================================================================


class SubstrateState(BaseModel):
    """
    State object passed through the LangGraph DAG.

    Contains the packet being processed and accumulated results.
    """

    envelope: PacketEnvelope
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
