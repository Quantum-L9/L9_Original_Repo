"""
L9 Packet Envelope Schema
Version: 1.0.1 (DEPRECATED)

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
    from core.schemas.packet_envelope import PacketEnvelope
    
    # NEW (canonical)
    from core.schemas import PacketEnvelope

Generated from: Memory.yaml v1.0.1
Module ID: memory.packet_envelope.v1.0.1
Status: DEPRECATED

Canonical event container used by the Memory Substrate.
Immutable once written.

Contracts:
- PacketEnvelope must be immutable once written.
- Embedding vectors are stored in a separate semantic_memory table (not inline).
- payload is arbitrary JSON and not variant-typed in v1.0.1.
- Only packet_type, payload, timestamp are guaranteed.
"""

import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Emit deprecation warning on import
warnings.warn(
    "core.schemas.packet_envelope is deprecated (v1.0.1). "
    "Use core.schemas.packet_envelope_v2 instead. "
    "Sunset date: 2026-04-05",
    DeprecationWarning,
    stacklevel=2,
)


# =============================================================================
# Enums (required by research_factory_nodes)
# =============================================================================


class PacketKind(str, Enum):
    """Kind of packet for routing/classification."""

    EVENT = "event"
    INSIGHT = "insight"
    RESULT = "result"
    ERROR = "error"
    COMMAND = "command"
    QUERY = "query"


# =============================================================================
# Supporting Models (required by research_factory_nodes)
# =============================================================================


class TokenUsage(BaseModel):
    """Token usage tracking for LLM calls."""

    prompt_tokens: int = Field(0, description="Input tokens used")
    completion_tokens: int = Field(0, description="Output tokens generated")
    total_tokens: int = Field(0, description="Total tokens consumed")

    model_config = {"frozen": True}


class SimpleContent(BaseModel):
    """Simple text content wrapper."""

    text: str = Field(..., description="Text content")
    format: str = Field("text", description="Content format (text, markdown, etc.)")

    model_config = {"frozen": True}


class StructuredReasoningBlock(BaseModel):
    """Structured reasoning output from LLM."""

    step: int = Field(..., description="Reasoning step number")
    thought: str = Field(..., description="Reasoning thought")
    action: Optional[str] = Field(None, description="Action taken")
    observation: Optional[str] = Field(None, description="Observation/result")

    model_config = {"frozen": True}


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
    source_agent: Optional[str] = Field(None, description="Source agent identifier")

    model_config = {"frozen": True}


class PacketMetadata(BaseModel):
    """Metadata attached to a packet envelope."""

    schema_version: Optional[str] = Field("1.0.1", description="Schema version")
    agent: Optional[str] = Field(None, description="Agent identifier")
    domain: Optional[str] = Field(None, description="Domain context")

    model_config = {"frozen": True, "extra": "allow"}


class PacketEnvelope(BaseModel):
    """
    Canonical event container used by the Memory Substrate.

    Matches the v1.0 repository implementation in substrate_models.py.
    IMMUTABLE once written.

    Contracts:
    - PacketEnvelope must be immutable once written.
    - Embedding vectors are stored in a separate semantic_memory table (not inline).
    - payload is arbitrary JSON and not variant-typed in v1.0.1.
    - Only packet_type, payload, timestamp are guaranteed.
    """

    # Primary Key
    packet_id: UUID = Field(
        default_factory=uuid4, description="Unique packet identifier"
    )

    # Required Fields
    packet_type: str = Field(
        ...,
        min_length=1,
        description="Semantic category of the packet (e.g., event, message)",
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Flexible JSON-like structure. Repository does not enforce shape.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp (generated automatically)",
    )

    # Optional Fields
    metadata: Optional[PacketMetadata] = Field(None)
    provenance: Optional[PacketProvenance] = Field(None)
    confidence: Optional[PacketConfidence] = Field(None)

    model_config = {
        "frozen": True,  # IMMUTABILITY ENFORCED
        "validate_assignment": True,
        "extra": "forbid",
    }

    def with_update(self, **updates) -> "PacketEnvelope":
        """
        Create a new PacketEnvelope with updates, linking to this as parent.

        This is the ONLY way to "modify" a packet (immutability preserved).
        """
        new_provenance = PacketProvenance(
            parent_packet=self.packet_id,
            source_agent=self.provenance.source_agent if self.provenance else None,
        )
        return self.model_copy(
            update={
                "packet_id": uuid4(),
                "provenance": new_provenance,
                "timestamp": datetime.utcnow(),
                **updates,
            }
        )


class PacketEnvelopeIn(BaseModel):
    """
    Input structure used for writes.
    Converted internally to PacketEnvelope.
    """

    packet_type: str = Field(
        ..., min_length=1, description="Semantic category of the packet"
    )
    payload: dict[str, Any] = Field(..., description="Flexible JSON-like structure")
    metadata: Optional[dict[str, Any]] = Field(None)
    provenance: Optional[dict[str, Any]] = Field(None)
    confidence: Optional[dict[str, Any]] = Field(None)

    def to_envelope(self) -> PacketEnvelope:
        """Convert input to full PacketEnvelope with defaults."""
        return PacketEnvelope(
            packet_id=uuid4(),
            packet_type=self.packet_type,
            payload=self.payload,
            timestamp=datetime.utcnow(),
            metadata=PacketMetadata(**self.metadata) if self.metadata else None,
            provenance=PacketProvenance(**self.provenance) if self.provenance else None,
            confidence=PacketConfidence(**self.confidence) if self.confidence else None,
        )


# =============================================================================
# Packet Write Response
# =============================================================================


class PacketWriteResult(BaseModel):
    """Returned after DAG processing for a packet write."""

    status: str = Field(..., description="'ok' or 'error'")
    packet_id: UUID = Field(..., description="Echoed packet ID")
    written_tables: list[str] = Field(
        default_factory=list, description="Tables updated"
    )
    error_message: Optional[str] = Field(
        None, description="Error details if status='error'"
    )


# =============================================================================
# Semantic Search Models
# =============================================================================


class SemanticSearchRequest(BaseModel):
    """Request to search semantic memory."""

    query: str = Field(..., min_length=1, description="Natural language query")
    top_k: int = Field(10, ge=1, le=100, description="Number of neighbors to return")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")


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
