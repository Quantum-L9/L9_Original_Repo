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

# ============================================================================
__dora_meta__ = {
    "component_name": "Database DTOs and Memory-Specific Models",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "substrate_models",
    "type": "enum",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [
            "ci.check_schema_deprecation",
            "memory.__init__",
            "memory.identity_tier",
            "memory.insight_extraction",
            "memory.retrieval",
            "memory.substrate_dag",
            "memory.substrate_repository",
            "memory.timeline_service",
            "memory.tool_audit",
            "scripts.migrate_substrate_models",
        ],
    },
}
# ============================================================================

from datetime import datetime, timezone, UTC
from enum import Enum
from typing import Any
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
    reasoning_block: StructuredReasoningBlock | None = None
    written_tables: list[str] = Field(default_factory=list)
    embedding_generated: bool = False
    checkpoint_saved: bool = False
    errors: list[str] = Field(default_factory=list)

    class Config:
        """
        Config class for customizing Pydantic model behavior in substrate memory models.
        Args:
            arbitrary_types_allowed: Enables use of arbitrary types in model fields.
        """

        arbitrary_types_allowed = True


# =============================================================================
# Database Row DTOs
# =============================================================================


class AgentMemoryEventRow(BaseModel):
    """DTO for agent_memory_events table."""

    event_id: UUID
    agent_id: str
    timestamp: datetime
    packet_id: UUID | None
    event_type: str
    content: dict[str, Any]


class SemanticMemoryRow(BaseModel):
    """DTO for semantic_memory table."""

    embedding_id: UUID
    agent_id: str | None
    vector: list[float]  # 1536 dimensions
    payload: dict[str, Any]
    created_at: datetime


class ReasoningTraceRow(BaseModel):
    """DTO for reasoning_traces table."""

    trace_id: UUID
    agent_id: str
    packet_id: UUID | None
    steps: dict[str, Any] | None
    extracted_features: dict[str, Any] | None
    inference_steps: list[dict[str, Any]] | None
    reasoning_tokens: list[str] | None
    decision_tokens: list[str] | None
    confidence_scores: dict[str, float] | None
    created_at: datetime


class PacketStoreRow(BaseModel):
    """DTO for packet_store table (v2.0 - all columns from migrations 0001, 0002, 0008)."""

    # Core fields (migration 0001)
    packet_id: UUID
    packet_type: str
    envelope: dict[str, Any]
    timestamp: datetime
    routing: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None

    # Threading & lineage (migration 0002)
    thread_id: UUID | None = None
    parent_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    ttl: datetime | None = None

    # 10X Enhancements (migration 0008)
    scope: str | None = "shared"
    importance_score: float | None = 0.5
    access_count: int | None = 0
    last_accessed: datetime | None = None
    confidence_updated_at: datetime | None = None
    contradiction_count: int | None = 0
    chunk_count: int | None = 1
    is_chunked: bool | None = False
    content_hash: str | None = None
    processing_status: str | None = "complete"

    # Multi-tenant identity (migration 0008)
    tenant_id: UUID | None = None
    org_id: UUID | None = None
    user_id: UUID | None = None
    correlation_id: UUID | None = None

    # Tracing (migration 0008)
    session_id: str | None = None
    trace_id: str | None = None


class GraphCheckpointRow(BaseModel):
    """DTO for graph_checkpoints table."""

    checkpoint_id: UUID
    agent_id: str
    graph_state: dict[str, Any]
    updated_at: datetime
    reason: str | None = None  # Added in migration 0014, optional for backward compat
    checkpoint_number: int | None = None  # Added in migration 0014


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
    source_packet: UUID | None = Field(None, description="Originating packet ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeFactRow(BaseModel):
    """DTO for knowledge_facts table (v2.0 - all columns from migrations 0005, 0008, 0010)."""

    # Core fields (migration 0005)
    fact_id: UUID
    subject: str
    predicate: str
    object: Any
    confidence: float | None = 0.8
    source_packet: UUID | None = None
    created_at: datetime

    # Entity normalization (migration 0008)
    subject_normalized: str | None = None
    object_normalized: str | None = None
    object_type: str | None = "value"

    # Confidence decay tracking (migration 0008)
    confidence_updated_at: datetime | None = None
    contradiction_count: int | None = 0
    supporting_packet_count: int | None = 1

    # Access tracking (migration 0008)
    access_count: int | None = 0
    last_accessed: datetime | None = None

    # Scope (migration 0008)
    scope: str | None = "shared"

    # Multi-tenant identity (migration 0008)
    tenant_id: UUID | None = None
    org_id: UUID | None = None
    user_id: UUID | None = None
    correlation_id: UUID | None = None

    # Deprecation (migration 0010)
    deprecated: bool | None = False
    deprecated_at: datetime | None = None
    deprecated_reason: str | None = None


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
    source_packet: UUID | None = None
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
    (after core writes have been completed by the canonical write path).

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
    reasoning_trace: StructuredReasoningBlock | None = Field(
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


# =============================================================================
# Semantic Facts Row DTO (Migration 0018 - Memory Spec v3.1)
# =============================================================================


class SemanticFactRow(BaseModel):
    """
    DTO for semantic_facts table (frontier-grade fact storage).

    Supports triplet structure, importance scoring, and tiered memory.
    Part of dual semantic+episodic memory architecture.
    """

    fact_id: UUID

    # Ownership
    tenant_id: UUID
    org_id: UUID
    user_id: UUID
    agent_id: str | None = None

    # Fact content
    fact_text: str
    triplet: dict[str, Any] = Field(
        default_factory=dict
    )  # {subject, predicate, object}

    # Embedding (optional - not always loaded)
    embedding: list[float] | None = (
        None  # 1536 dimensions (truncated from text-embedding-3-large)
    )

    # Importance and ranking
    importance: float = 0.5
    access_count: int = 0
    last_accessed: datetime | None = None

    # Categorization
    tags: list[str] = Field(default_factory=list)
    tier: str = "general"  # identity, project, session, general

    # Source tracking
    source: str | None = None
    source_packet_id: UUID | None = None

    # Confidence and validation
    confidence: float = 0.8
    validated_at: datetime | None = None
    validated_by: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Episodic Events Row DTO (Migration 0019 - Memory Spec v3.1)
# =============================================================================


class EpisodicEventRow(BaseModel):
    """
    DTO for episodic_events table (temporal event storage).

    Stores events with timestamps, entities, and decay factors.
    Part of dual semantic+episodic memory architecture.
    """

    event_id: UUID

    # Ownership
    tenant_id: UUID
    org_id: UUID
    user_id: UUID
    agent_id: str | None = None

    # Event content
    observation: str  # What happened
    event_type: str = "general"

    # Temporal information (CRITICAL)
    event_timestamp: datetime  # When it occurred
    duration_seconds: int | None = None

    # Entity references
    entities: list[str] = Field(default_factory=list)

    # Context and outcome
    context: dict[str, Any] = Field(default_factory=dict)
    outcome: str | None = None

    # Importance and ranking
    severity: float = 0.5
    impact_score: float = 0.5

    # Lineage
    source_packet_id: UUID | None = None
    parent_event_id: UUID | None = None

    # Session/thread grouping
    session_id: UUID | None = None
    thread_id: UUID | None = None

    # Decay and retention
    decay_factor: float = 1.0
    last_recalled: datetime | None = None
    recall_count: int = 0

    # Timestamps
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Episodic-Semantic Link Row DTO (Migration 0019 - Memory Spec v3.1)
# =============================================================================


class EpisodicSemanticLinkRow(BaseModel):
    """
    DTO for episodic_semantic_links junction table.

    Links episodic events to semantic facts (many-to-many).
    Enables queries like "find all events involving fact X".
    """

    link_id: UUID
    event_id: UUID
    fact_id: UUID

    # Link metadata
    relationship_type: str = "involves"  # involves, confirms, contradicts, updates
    strength: float = 1.0

    # Timestamp
    created_at: datetime


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "data-models",
        "enum",
        "event-driven",
        "learning",
        "metrics",
        "migration",
        "pydantic",
        "security",
        "testing",
    ],
    "keywords": [
        "added",
        "agent",
        "block",
        "changelog",
        "checkpoint",
        "core",
        "database",
        "dtos",
    ],
    "business_value": "Database row DTOs (PacketStoreRow, KnowledgeFactRow, etc.) Memory-specific models (StructuredReasoningBlock, SubstrateState) Knowledge extraction models (KnowledgeFact, ExtractedInsight) Enrichment pi",
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
