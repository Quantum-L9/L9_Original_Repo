"""
L9 Memory Substrate - LangGraph DAG (Ingestion Pipeline)
Version: 1.1.0

NOTE: This is a LangGraph processing DAG for packet ingestion, NOT a Neo4j graph client.
      For Neo4j graph operations, see graph_client.py.

Implements the substrate processing pipeline as a LangGraph DAG:
  intake_node → reasoning_node → memory_write_node → graph_sync_node → semantic_embed_node → checkpoint_node

The DAG routes PacketEnvelopes through processing stages with state accumulation.

All memory operations flow through MCP-Memory's unified ingestion pipeline.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "LangGraph DAG (Ingestion Pipeline)",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "substrate_dag",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "core.tools.base_registry",
            "memory.__init__",
            "memory.ingestion",
            "memory.substrate_dag_wrapper",
            "memory.substrate_service",
            "tests.memory.test_embedding_filter",
            "tests.memory.test_ingestion_pipeline_audit",
            "tests.memory.test_mcp_bypass_compliance",
            "tests.memory.test_substrate_dag_native",
            "tests.memory.test_unified_pipeline",
        ],
    },
}
# ============================================================================

import asyncio
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import UUID, uuid4

import structlog
from langgraph.graph import END, StateGraph

from core.decorators import must_stay_async
from core.schemas import PacketEnvelope, PacketMetadata, PacketWriteResult
from memory.graph_client import get_neo4j_client
from memory.substrate_models import (
    EnrichmentResult,
    ExtractedInsight,
    KnowledgeFact,
    StructuredReasoningBlock,
)

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

logger = structlog.get_logger(__name__)


# =============================================================================
# Embedding Skip Patterns (GMP-42: Filter low-value content from semantic index)
# =============================================================================

# These patterns are generic error/fallback messages that pollute semantic search.
# They carry no semantic information and should NOT be embedded.
SKIP_EMBEDDING_PATTERNS: list[str] = [
    # L's generic error responses
    "Sorry, I encountered a temporary error. Please try again.",
    "Sorry, I encountered an error processing your command.",
    # Empty/fallback responses
    "No response generated.",
    "This message has already been processed.",
    # L9 agent unavailable
    "L9 agent executor not available. Please try again later.",
    # Mac agent unavailable
    "Mac agent is not available on this server.",
]


def _should_skip_embedding(text: str) -> bool:
    """
    Check if text matches known low-value patterns that should not be embedded.

    Args:
        text: The text content to check

    Returns:
        True if text should be skipped, False otherwise
    """
    if not text:
        return True

    text_stripped = text.strip()

    # Exact match against known patterns
    if text_stripped in SKIP_EMBEDDING_PATTERNS:
        return True

    # Pattern-based checks for variations
    low_value_prefixes = [
        "Sorry, I encountered",  # Error message variants
        "❌ Mac command error:",  # Mac error prefix
        "❌ Please provide a command",  # Help text
    ]
    for prefix in low_value_prefixes:
        if text_stripped.startswith(prefix):
            return True

    # Skip very short content (less than 10 chars, likely noise)
    return len(text_stripped) < 10


# =============================================================================
# Config Helper (for RunnableConfig dependency injection)
# =============================================================================


def _get_config_dependency(
    config: RunnableConfig, key: str, default: Any = None
) -> Any:
    """
    Safely extract a configurable dependency from RunnableConfig.

    Args:
        config: RunnableConfig or None
        key: Key to extract from configurable dict
        default: Default value if not found

    Returns:
        The dependency value or default
    """
    if not config:
        return default
    configurable = config.get("configurable", {})
    if not configurable:
        return default
    return configurable.get(key, default)


# =============================================================================
# State Definition
# =============================================================================


class SubstrateGraphState(TypedDict):
    """
    State passed through the LangGraph DAG.

    Accumulates results from each processing node.

    Note: Uses Optional[] for LangGraph compatibility.
    LangGraph's get_type_hints() evaluates types at runtime.
    """

    # Input
    envelope: dict[str, Any]  # PacketEnvelope as dict

    # Processing results
    reasoning_block: dict[str, Any] | None  # StructuredReasoningBlock if generated
    written_tables: list[str]
    embedding_id: str | None
    saved_checkpoint_id: (
        str | None
    )  # Renamed from checkpoint_id (reserved in LangGraph)

    # Insight extraction results (v1.1.0+)
    insights: list[dict[str, Any]]  # ExtractedInsight objects as dicts
    facts: list[dict[str, Any]]  # KnowledgeFact objects as dicts
    world_model_triggered: bool

    # Status
    errors: list[str]


def _default_state() -> SubstrateGraphState:
    """Create default state."""
    return {
        "envelope": {},
        "reasoning_block": None,
        "written_tables": [],
        "embedding_id": None,
        "saved_checkpoint_id": None,
        "insights": [],
        "facts": [],
        "world_model_triggered": False,
        "errors": [],
    }


# =============================================================================
# Node Functions
# =============================================================================


@must_stay_async("callers use await")
async def intake_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Entry node: validates and normalizes the PacketEnvelope.

    Responsibilities (GMP-SDAG Option A — service layer authoritative):
    - Validates required fields (packet_type, payload)
    - Ensures packet_id and timestamp are set
    - Checks for duplicate packets (prevents reprocessing)
    - Prepares state for downstream processing

    NOTE: Governance enforcement and audit preparation are handled by
    substrate_service.write_packet() BEFORE the DAG runs. This node
    receives already-governed, already-audited envelopes.
    """

    repository = _get_config_dependency(config, "repository")
    logger.debug("intake_node: Processing packet")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))

    # --- Field Validation ---
    if not envelope.get("packet_type"):
        errors.append("Missing required field: packet_type")
    if not envelope.get("payload"):
        errors.append("Missing required field: payload")

    if errors:
        return {**state, "envelope": envelope, "errors": errors}

    # --- Ensure Defaults ---
    if not envelope.get("packet_id"):
        envelope["packet_id"] = str(uuid4())
    if not envelope.get("timestamp"):
        envelope["timestamp"] = datetime.now(UTC).isoformat()
    if not envelope.get("metadata"):
        envelope["metadata"] = {
            "schema_version": "1.0.0",
            "reasoning_mode": None,
            "agent": None,
            "domain": "l9",
        }

    # --- Governance & Audit: HANDLED BY substrate_service.write_packet() ---
    # Option A (GMP-SDAG): Service layer is authoritative for governance enforcement,
    # audit preparation, and packet validation. intake_node only handles structural
    # defaults and duplicate detection. This avoids double-governance and eliminates
    # the soft-fail security gap that existed when governance was in this node.

    # --- Duplicate Detection ---
    packet_id = envelope.get("packet_id")
    if packet_id and repository:
        try:
            if hasattr(repository, "check_packet_exists"):
                exists = await repository.check_packet_exists(UUID(str(packet_id)))
                if exists:
                    errors.append(f"Duplicate packet: {packet_id} already processed")
                    logger.warning(
                        "intake_node: Duplicate packet detected",
                        packet_id=str(packet_id),
                    )
        except Exception as e:
            logger.warning(
                "intake_node: Duplicate check failed",
                packet_id=str(packet_id),
                error=str(e),
            )

    logger.debug(
        "intake_node: Processed packet",
        packet_id=envelope.get("packet_id"),
    )

    return {**state, "envelope": envelope, "errors": errors}


@must_stay_async("callers use await")
async def reasoning_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Reasoning node: generates StructuredReasoningBlock from packet.

    - Extracts features from payload
    - Records inference steps
    - Generates confidence scores
    - Determines memory write operations
    """
    # Note: repository not used in this node (reserved for future reasoning persistence)
    logger.debug("reasoning_node: Generating reasoning block")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))

    # Skip if previous errors
    if errors:
        logger.warning("reasoning_node: Skipping due to previous errors")
        return state

    packet_id = envelope.get("packet_id")
    payload = envelope.get("payload", {})
    packet_type = envelope.get("packet_type", "unknown")

    # Generate reasoning block
    reasoning_block = {
        "block_id": str(uuid4()),
        "packet_id": packet_id,
        "timestamp": datetime.now(UTC).isoformat(),
        # Feature extraction (simplified - would be LLM-powered in production)
        "extracted_features": {
            "packet_type": packet_type,
            "payload_keys": list(payload.keys()),
            "payload_size": len(str(payload)),
        },
        # Inference steps
        "inference_steps": [
            {"step": 1, "action": "validate_packet", "result": "valid"},
            {"step": 2, "action": "extract_features", "result": "extracted"},
            {"step": 3, "action": "determine_write_targets", "result": packet_type},
        ],
        # Token sequences (placeholder for actual reasoning traces)
        "reasoning_tokens": [
            f"packet_type:{packet_type}",
            f"payload_keys:{','.join(payload.keys())[:50]}",
        ],
        "decision_tokens": [
            "store_packet:true",
            f"embed_payload:{'semantic' in packet_type.lower() or 'memory' in packet_type.lower()}",
        ],
        # Confidence scores
        "confidence_scores": {
            "validation": 1.0,
            "feature_extraction": 0.9,
            "routing": 0.85,
        },
        # Memory operations to perform
        "memory_write_ops": [
            {"table": "packet_store", "operation": "insert"},
            {"table": "agent_memory_events", "operation": "insert"},
        ],
    }

    # Add reasoning trace write op if significant reasoning occurred
    if packet_type in ("reasoning_trace", "inference", "decision"):
        write_ops = reasoning_block["memory_write_ops"]
        if isinstance(write_ops, list):
            write_ops.append(
                {"table": "reasoning_traces", "operation": "insert"}
            )

    logger.debug(f"reasoning_node: Generated block {reasoning_block['block_id']}")

    return {
        **state,
        "reasoning_block": reasoning_block,
    }


@must_stay_async("callers use await")
async def memory_write_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Memory write node: persists packet and reasoning to database.

    Writes to:
    - packet_store
    - agent_memory_events
    - reasoning_traces (if reasoning block present)
    """
    repository = _get_config_dependency(config, "repository")
    logger.debug("memory_write_node: Writing to database")

    envelope = state.get("envelope", {})
    reasoning_block = state.get("reasoning_block")
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))

    # Skip if previous errors
    if errors:
        logger.warning("memory_write_node: Skipping due to previous errors")
        return state

    # Repository will be injected at runtime
    if repository is None:
        logger.warning("memory_write_node: No repository provided, skipping DB writes")
        errors.append("memory_write_node: No repository — DB writes skipped")
        return {
            **state,
            "written_tables": written_tables,
            "errors": errors,
        }

    try:
        # Write packet
        packet = PacketEnvelope(**envelope)
        await repository.insert_packet(packet)
        written_tables.append("packet_store")

        # Write memory event
        agent_id = envelope.get("metadata", {}).get("agent") or "default"
        await repository.insert_memory_event(
            agent_id=agent_id,
            event_type=envelope.get("packet_type", "unknown"),
            content=envelope.get("payload", {}),
            packet_id=packet.packet_id,
            timestamp=packet.timestamp,
        )
        written_tables.append("agent_memory_events")

        # Write reasoning trace if present
        if reasoning_block:
            block = StructuredReasoningBlock(**reasoning_block)
            await repository.insert_reasoning_block(block)
            written_tables.append("reasoning_traces")

        logger.debug(f"memory_write_node: Wrote to {written_tables}")

    except Exception as e:
        logger.error(f"memory_write_node: Write failed: {e}")
        errors.append(f"memory_write_node error: {e!s}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


@must_stay_async("callers use await")
async def graph_sync_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Neo4j graph sync node: syncs packet to knowledge graph.

    Creates:
    - Event node for the packet
    - Agent entity (if agent_id present)
    - Thread entity (if thread_id present)
    - Relationships between Event ↔ Agent ↔ Thread

    This is best-effort - failures don't block the pipeline.
    GMP-NEO4J-DAG: Added to enable WorldModel graph queries.
    """
    logger.debug("graph_sync_node: Syncing to Neo4j")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))

    # Skip if previous errors (core writes failed)
    if errors:
        logger.warning("graph_sync_node: Skipping due to previous errors")
        return state

    # Best-effort Neo4j sync - don't fail pipeline on graph errors
    try:
        neo4j = await get_neo4j_client()
        if not neo4j or not neo4j.is_available():
            logger.debug("graph_sync_node: Neo4j not available, skipping")
            return state

        packet_id = envelope.get("packet_id", str(uuid4()))
        packet_type = envelope.get("packet_type", "unknown")
        timestamp = envelope.get("timestamp", datetime.now(UTC).isoformat())
        metadata = envelope.get("metadata", {})
        agent_id = metadata.get("agent") if metadata else None
        thread_id = (
            str(envelope.get("thread_id")) if envelope.get("thread_id") else None
        )
        tags = envelope.get("tags", [])

        # Extract parent event ID from lineage (if present)
        lineage = envelope.get("lineage", {})
        parent_ids = lineage.get("parent_ids", []) if lineage else []
        parent_event_id = str(parent_ids[0]) if parent_ids else None

        # Create Event node for this packet
        await neo4j.create_event(
            event_id=str(packet_id),
            event_type=packet_type,
            timestamp=timestamp
            if isinstance(timestamp, str)
            else timestamp.isoformat(),
            properties={
                "packet_type": packet_type,
                "agent": agent_id,
                "thread_id": thread_id,
                "tags": tags,
            },
            parent_event_id=parent_event_id,
        )

        # Link to Agent entity (create if not exists)
        if agent_id:
            await neo4j.create_entity(
                entity_type="Agent",
                entity_id=agent_id,
                properties={"name": agent_id, "type": "agent"},
            )
            await neo4j.create_relationship(
                from_type="Event",
                from_id=str(packet_id),
                to_type="Agent",
                to_id=agent_id,
                rel_type="PROCESSED_BY",
            )

        # Link to Thread (conversation grouping)
        if thread_id:
            await neo4j.create_entity(
                entity_type="Thread",
                entity_id=thread_id,
                properties={"id": thread_id, "type": "conversation"},
            )
            await neo4j.create_relationship(
                from_type="Event",
                from_id=str(packet_id),
                to_type="Thread",
                to_id=thread_id,
                rel_type="PART_OF",
            )

        written_tables.append("neo4j_graph")
        logger.debug(f"graph_sync_node: Synced packet {packet_id} to Neo4j")

    except Exception as e:
        # Best-effort: log warning but don't fail pipeline
        logger.warning(f"graph_sync_node: Neo4j sync failed (non-critical): {e}")
        # Don't append to errors - Neo4j is optional enhancement

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


@must_stay_async("callers use await")
async def semantic_embed_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Semantic embedding node: generates and stores embedding for payload.

    Uses canonical text_utils.extract_embeddable_text() for consistent
    field priority across all pipelines.
    """
    from memory.text_utils import extract_embeddable_text, should_skip_embedding

    semantic_service = _get_config_dependency(config, "semantic_service")
    logger.debug("semantic_embed_node: Processing embedding")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))
    embedding_id = None

    if errors:
        logger.warning("semantic_embed_node: Skipping due to previous errors")
        return state

    # Security flag: skip if injection markers detected in intake_node
    metadata = envelope.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("_security_skip_embed"):
        logger.debug("semantic_embed_node: Skipping due to security flag")
        return state

    payload = envelope.get("payload", {})

    # Canonical text extraction (SINGLE SOURCE OF TRUTH)
    text_to_embed = extract_embeddable_text(payload)

    if text_to_embed is None:
        logger.debug("semantic_embed_node: No embeddable content found")
        return state

    # GMP-42: Skip low-value content
    if should_skip_embedding(text_to_embed):
        logger.debug(
            "semantic_embed_node: Low-value content skipped",
            text_preview=text_to_embed[:50],
        )
        return state

    if semantic_service is None:
        logger.warning("semantic_embed_node: No semantic service, skipping")
        return state

    try:
        agent_id = metadata.get("agent") if isinstance(metadata, dict) else None
        scope = (
            (metadata.get("db_scope") or metadata.get("scope") or "cursor")
            if isinstance(metadata, dict)
            else "cursor"  # Default to valid DB scope
        )

        # Include tags in payload for tag-aware retrieval (filter/boost)
        envelope_tags = envelope.get("tags") or []

        embedding_id = await semantic_service.embed_and_store(
            text=text_to_embed,
            payload={
                "packet_id": envelope.get("packet_id"),
                "packet_type": envelope.get("packet_type", ""),
                "source_payload": payload,
                "tags": envelope_tags,
            },
            agent_id=agent_id,
            scope=scope,
        )
        written_tables.append("semantic_memory")
        logger.debug(
            "semantic_embed_node: Created embedding",
            embedding_id=str(embedding_id),
            scope=scope,
        )

    except Exception as e:
        logger.error("semantic_embed_node: Embedding failed", error=str(e))
        errors.append(f"semantic_embed_node error: {e!s}")

    return {
        **state,
        "embedding_id": embedding_id,
        "written_tables": written_tables,
        "errors": errors,
    }


@must_stay_async("callers use await")
async def checkpoint_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Checkpoint node: saves graph state for recovery.

    Final node in the DAG - persists state to graph_checkpoints.
    """
    repository = _get_config_dependency(config, "repository")
    logger.debug("checkpoint_node: Saving checkpoint")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))
    checkpoint_id = None

    agent_id = envelope.get("metadata", {}).get("agent") or "default"

    if repository is None:
        logger.warning("checkpoint_node: No repository, skipping checkpoint")
        return {
            **state,
            "saved_checkpoint_id": "skipped",
        }

    try:
        # Save checkpoint with current state
        checkpoint_id = await repository.save_checkpoint(
            agent_id=agent_id,
            graph_state={
                "packet_id": envelope.get("packet_id"),
                "packet_type": envelope.get("packet_type"),
                "written_tables": written_tables,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        written_tables.append("graph_checkpoints")
        logger.debug(f"checkpoint_node: Saved checkpoint {checkpoint_id}")

    except Exception as e:
        logger.error(f"checkpoint_node: Checkpoint failed: {e}")
        errors.append(f"checkpoint_node error: {e!s}")

    return {
        **state,
        "saved_checkpoint_id": str(checkpoint_id) if checkpoint_id else None,
        "written_tables": written_tables,
        "errors": errors,
    }


# =============================================================================
# Insight Extraction Nodes (v1.1.0+)
# =============================================================================


@must_stay_async("callers use await")
async def extract_insights_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Extract insights, facts, and entities from packet payload and reasoning block.

    Combines:
    - Heuristic key-value fact extraction from structured payload
    - Reasoning block conclusion extraction
    - **Unified EntityExtractionService** (4-tier: metadata, pattern, heuristic, LLM)
      for entity recognition across text, payload, and metadata.
    """
    logger.debug("extract_insights_node: Extracting insights")

    envelope = state.get("envelope", {})
    reasoning_block = state.get("reasoning_block")
    errors = list(state.get("errors", []))

    # Skip if previous errors
    if errors:
        logger.warning("extract_insights_node: Skipping due to previous errors")
        return state

    payload = envelope.get("payload", {})
    packet_id = envelope.get("packet_id")
    packet_type = envelope.get("packet_type", "")
    metadata = envelope.get("metadata", {})

    insights = []
    facts = []

    # Heuristic 1: Extract facts from structured payload
    for key, value in payload.items():
        if key in ("id", "timestamp", "created_at", "updated_at"):
            continue

        # Skip complex nested structures for now
        if isinstance(value, dict) and len(str(value)) > 500:
            continue

        # Convert UUID values to strings for JSON serialization
        object_value = str(value) if isinstance(value, UUID) else value
        source_packet_str = str(packet_id) if isinstance(packet_id, UUID) else packet_id

        fact = {
            "fact_id": str(uuid4()),
            "subject": payload.get(
                "subject", payload.get("entity", payload.get("name", packet_type))
            ),
            "predicate": key,
            "object": object_value,
            "confidence": 0.8,
            "source_packet": source_packet_str,
            "created_at": datetime.now(UTC).isoformat(),
        }
        facts.append(fact)

    # Heuristic 2: Extract insights from reasoning block conclusions
    if reasoning_block:
        decision_tokens = reasoning_block.get("decision_tokens", [])
        confidence_scores = reasoning_block.get("confidence_scores", {})

        # Look for high-confidence decisions
        for token in decision_tokens:
            if ":" in token:
                key, value = token.split(":", 1)
                if key.strip() in ("store_packet", "embed_payload", "route_to"):
                    insight = {
                        "insight_id": str(uuid4()),
                        "insight_type": "conclusion",
                        "content": f"Reasoning determined {key}={value}",
                        "entities": [metadata.get("agent", "unknown")],
                        "confidence": confidence_scores.get("routing", 0.7),
                        "source_packet": packet_id,
                        "facts": [],
                        "trigger_world_model": value.lower() == "true"
                        and key == "store_packet",
                    }
                    insights.append(insight)

    # Heuristic 3: Extract pattern-based insights from text content
    text_content = (
        payload.get("text")
        or payload.get("content")
        or payload.get("description")
        or ""
    )
    if text_content and isinstance(text_content, str) and len(text_content) > 50:
        insight = {
            "insight_id": str(uuid4()),
            "insight_type": "pattern",
            "content": f"Text content detected in {packet_type} packet ({len(text_content)} chars)",
            "entities": [],
            "confidence": 0.6,
            "source_packet": packet_id,
            "facts": [],
            "trigger_world_model": False,
        }
        insights.append(insight)

    # ---- Unified Entity Extraction (Phase 4.2) ----
    # Uses EntityExtractionService for 4-tier entity recognition:
    # metadata → pattern (regex) → heuristic (payload structure) → LLM (optional)
    extracted_entities = []
    try:
        from memory.entity_extraction import EntityExtractionService

        entity_service = EntityExtractionService(use_llm=False)
        extracted_entities = await entity_service.extract(
            text=text_content if isinstance(text_content, str) else None,
            payload=payload,
            metadata_context={
                "agent_id": metadata.get("agent"),
                "source_id": envelope.get("source_id"),
                "thread_id": envelope.get("thread_id"),
            },
        )

        # Convert extracted entities to insight format for downstream consumers
        if extracted_entities:
            entity_names = [e.name for e in extracted_entities[:20]]
            entity_insight = {
                "insight_id": str(uuid4()),
                "insight_type": "entity_extraction",
                "content": f"Extracted {len(extracted_entities)} entities: {', '.join(entity_names[:5])}{'...' if len(entity_names) > 5 else ''}",
                "entities": entity_names,
                "confidence": max(e.confidence for e in extracted_entities)
                if extracted_entities
                else 0.5,
                "source_packet": packet_id,
                "facts": [],
                "trigger_world_model": any(
                    e.entity_type in ("agent", "gmp_reference")
                    for e in extracted_entities
                ),
            }
            insights.append(entity_insight)

            # Also emit entity-level facts for knowledge graph
            source_packet_str = (
                str(packet_id) if isinstance(packet_id, UUID) else packet_id
            )
            for entity in extracted_entities[:20]:
                entity_fact = {
                    "fact_id": str(uuid4()),
                    "subject": entity.name,
                    "predicate": f"is_{entity.entity_type}",
                    "object": entity.entity_id,
                    "confidence": entity.confidence,
                    "source_packet": source_packet_str,
                    "created_at": datetime.now(UTC).isoformat(),
                }
                facts.append(entity_fact)

    except Exception as exc:
        # Entity extraction is non-critical — log and continue
        logger.warning(
            "extract_insights_node: Entity extraction failed (non-fatal)",
            error=str(exc),
        )

    logger.debug(
        "extract_insights_node: Extraction complete",
        insights_count=len(insights),
        facts_count=len(facts),
        entities_count=len(extracted_entities),
    )

    return {
        **state,
        "insights": insights,
        "facts": facts,
    }


@must_stay_async("callers use await")
async def store_insights_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Store extracted insights and facts to database (v2.1.0 - GMP-67).

    Persists two distinct data types to their correct tables:
    - **Facts** → knowledge_facts table via UPSERT (SPO triples, idempotent)
    - **Insights** → packet_store table as insight packets (native shape preserved)

    Facts use subject/predicate/object structure for graph queries.
    Insights keep their native schema (type, content, entities, confidence)
    and are stored as packets with packet_type matching the insight type.
    """
    from uuid import UUID

    repository = _get_config_dependency(config, "repository")
    logger.debug("store_insights_node: Storing insights and facts")

    insights = state.get("insights", [])
    facts = state.get("facts", [])
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))

    # Get packet_id from envelope for linking facts/insights to source packet
    envelope = state.get("envelope", {})
    packet_id_raw = envelope.get("packet_id")
    # Handle both UUID object and string cases
    if packet_id_raw:
        if isinstance(packet_id_raw, UUID):
            packet_id = packet_id_raw
        else:
            packet_id = UUID(str(packet_id_raw))
    else:
        packet_id = None

    # GMP-FIX: Get project_id and scope from source envelope metadata for insight packets
    # This ensures insight packets inherit project_id and scope from their source packet
    # to satisfy the packet_store_project_id_not_null constraint and scope isolation
    source_metadata = envelope.get("metadata", {})
    if isinstance(source_metadata, dict):
        source_project_id = source_metadata.get("project_id", "l9")
        source_scope = (
            source_metadata.get("scope") or source_metadata.get("db_scope") or "cursor"
        )
    else:
        # Handle PacketMetadata object
        source_project_id = getattr(source_metadata, "project_id", None) or "l9"
        source_scope = (
            getattr(source_metadata, "scope", None)
            or getattr(source_metadata, "db_scope", None)
            or "cursor"
        )

    if not insights and not facts:
        logger.debug("store_insights_node: No insights or facts to store")
        return state

    if repository is None:
        logger.warning("store_insights_node: No repository, skipping persistence")
        return state

    # -----------------------------------------------------------------
    # 1. Store facts → knowledge_facts table (SPO triples)
    # -----------------------------------------------------------------
    try:
        facts_inserted = 0
        for fact in facts:
            # Handle both dict and KnowledgeFact objects
            if isinstance(fact, dict):
                fact_id = fact.get("fact_id")
                subject = fact.get("subject")
                predicate = fact.get("predicate")
                object_value = fact.get("object")
                confidence = fact.get("confidence", 0.8)
                source_packet = fact.get("source_packet") or packet_id
            else:
                # KnowledgeFact model
                fact_id = fact.fact_id
                subject = fact.subject
                predicate = fact.predicate
                object_value = fact.object
                confidence = fact.confidence
                source_packet = fact.source_packet or packet_id

            # Ensure fact_id is UUID
            if fact_id and isinstance(fact_id, str):
                fact_id = UUID(fact_id)
            elif not fact_id:
                fact_id = uuid4()

            # Ensure source_packet is UUID
            if source_packet and isinstance(source_packet, str):
                source_packet = UUID(source_packet)
            elif isinstance(source_packet, UUID):
                pass  # Already UUID, keep as is

            # Ensure object_value is JSON-serializable (convert UUID to string)
            if isinstance(object_value, UUID):
                object_value = str(object_value)

            await repository.insert_knowledge_fact(
                fact_id=fact_id,
                subject=subject,
                predicate=predicate,
                object_value=object_value,
                confidence=confidence,
                source_packet=source_packet,
                scope=source_scope,  # Inherit scope from source packet
            )
            facts_inserted += 1

        if facts_inserted > 0:
            written_tables.append("knowledge_facts")
            logger.debug(
                "store_insights_node.facts_stored",
                count=facts_inserted,
                source_packet=str(packet_id),
            )

    except Exception as e:
        logger.error("store_insights_node.facts_failed", error=str(e))
        errors.append(f"store_insights_node facts error: {e!s}")

    # -----------------------------------------------------------------
    # 2. Store insights → packet_store as insight packets (native shape)
    #    Each insight becomes its own packet, linked to the source packet
    #    via metadata.source_packet_id. This preserves the insight's native
    #    schema (type, content, entities, domains, patterns, confidence)
    #    without forcing it into SPO triple format.
    # -----------------------------------------------------------------
    try:
        insights_inserted = 0
        for insight in insights:
            if isinstance(insight, dict):
                insight_type = insight.get("type", "insight")
                confidence = insight.get("confidence", 0.7)
                payload = dict(insight)  # preserve full native shape
            else:
                # ExtractedInsight model
                insight_type = getattr(insight, "insight_type", "insight")
                confidence = getattr(insight, "confidence", 0.7)
                payload = {
                    "insight_type": insight_type,
                    "content": getattr(insight, "content", ""),
                    "entities": getattr(insight, "entities", []),
                    "confidence": confidence,
                    "trigger_world_model": getattr(
                        insight, "trigger_world_model", False
                    ),
                }

            # Build a proper PacketEnvelope for the insight
            # GMP-FIX: Include project_id in metadata to satisfy DB constraint
            insight_envelope = PacketEnvelope(
                packet_type=insight_type,
                payload=payload,
                metadata=PacketMetadata(
                    schema_version="1.1.0",
                    agent="store_insights_node",
                    source_packet_id=str(packet_id) if packet_id else None,
                    project_id=source_project_id,  # Inherit from source packet
                ),
            )

            await repository.insert_packet(insight_envelope)
            insights_inserted += 1

        if insights_inserted > 0:
            written_tables.append("packet_store")
            logger.debug(
                "store_insights_node.insights_stored",
                count=insights_inserted,
                source_packet=str(packet_id),
            )

    except Exception as e:
        logger.error("store_insights_node.insights_failed", error=str(e))
        errors.append(f"store_insights_node insights error: {e!s}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


@must_stay_async("callers use await")
async def world_model_trigger_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Trigger world model update based on extracted insights.

    Calls WorldModelService.update_from_insights() if any
    insight has trigger_world_model=True.

    Integration:
    - Uses world_model.service.WorldModelService for DB-backed updates
    - Falls back to orchestrator if service not available
    """
    # Note: repository not used in this node (world_model_service handles persistence)
    world_model_service = _get_config_dependency(config, "world_model_service")
    logger.debug("world_model_trigger_node: Checking for world model updates")

    insights = state.get("insights", [])
    errors = list(state.get("errors", []))

    # Check if any insight should trigger world model
    should_trigger = any(
        insight.get("trigger_world_model", False) for insight in insights
    )

    if not should_trigger:
        logger.debug("world_model_trigger_node: No world model update needed")
        return {
            **state,
            "world_model_triggered": False,
        }

    # Try to use world model service (DB-backed)
    if world_model_service is None:
        try:
            from world_model.service import get_world_model_service

            world_model_service = get_world_model_service()
        except ImportError:
            logger.warning(
                "world_model_trigger_node: World model service not available"
            )
            return {
                **state,
                "world_model_triggered": False,
            }

    try:
        # Call world model service
        result = await world_model_service.update_from_insights(insights)
        logger.debug(f"world_model_trigger_node: World model updated: {result}")

        return {
            **state,
            "world_model_triggered": result.get("status") == "ok",
        }

    except Exception as e:
        logger.error(f"world_model_trigger_node: Update failed: {e}")
        errors.append(f"world_model_trigger_node error: {e!s}")
        return {
            **state,
            "world_model_triggered": False,
            "errors": errors,
        }


# =============================================================================
# Routing Functions (Conditional Edges)
# =============================================================================


def _extract_text_for_routing(envelope: dict) -> str:
    """Extract text content from envelope for routing decisions."""
    if not envelope:
        return ""
    payload = envelope.get("payload", {})
    if not isinstance(payload, dict):
        return ""
    return (
        payload.get("text")
        or payload.get("content")
        or payload.get("description")
        or ""
    )


def route_after_memory_write(state: SubstrateGraphState) -> str:
    """
    Route after memory_write_node: skip semantic_embed if low-value content.

    GMP-42: Implements skip pattern at graph level (more efficient than in-node check).

    Returns:
        "do_embed" to run semantic_embed_node
        "skip_embed" to skip directly to extract_insights_node
    """
    try:
        envelope = state.get("envelope", {})

        # Guard: empty or invalid envelope
        if not envelope:
            logger.warning(
                "route_after_memory_write: Empty envelope, defaulting to 'do_embed'"
            )
            return "do_embed"

        payload = envelope.get("payload", {})
        packet_type = envelope.get("packet_type", "")

        # Check if content type is embeddable
        # GMP-130: Expanded to include more packet types for semantic search
        should_embed = (
            "semantic" in packet_type.lower()
            or "memory" in packet_type.lower()
            or "response" in packet_type.lower()
            or "decision" in packet_type.lower()
            or "insight" in packet_type.lower()
            or "agent" in packet_type.lower()
            or "text" in payload
            or "content" in payload
            or "description" in payload
            or "message" in payload
            or "summary" in payload
            or "result" in payload
        )

        if not should_embed:
            logger.debug(
                f"route_after_memory_write: packet_type={packet_type} not embeddable, skip"
            )
            return "skip_embed"

        # Check GMP-42 skip patterns
        text = _extract_text_for_routing(envelope)
        if _should_skip_embedding(text):
            logger.debug("route_after_memory_write: GMP-42 skip pattern matched, skip")
            return "skip_embed"

        return "do_embed"

    except Exception as e:
        logger.error(
            f"route_after_memory_write: Error in routing: {e}, defaulting to 'do_embed'"
        )
        return "do_embed"


# =============================================================================
# DTB: Analogical Enrichment Node (feature-flagged via L9_ENABLE_DTB_MEMORY)
# =============================================================================

_DTB_MEMORY_ENABLED = os.getenv("L9_ENABLE_DTB_MEMORY", "false").lower() == "true"


async def analogical_enrichment_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Optional DTB node: find cross-domain analogies for the incoming packet.

    Stores any discovered analogies as additional insights in the state.
    This node is additive only — it never modifies the original packet.
    Failures are non-fatal and logged.
    """
    if not _DTB_MEMORY_ENABLED:
        return state

    try:
        from domain_tensor_bridge.analogical_reasoner import AnalogicalReasoner

        envelope = state.get("envelope", {})
        packet_type = envelope.get("packet_type", "unknown")
        payload = envelope.get("payload", "")

        reasoner = AnalogicalReasoner()
        context = {
            "domain": packet_type,
            "content": payload[:500]
            if isinstance(payload, str)
            else str(payload)[:500],
        }
        analogies = await reasoner.find_analogies(context)

        if analogies:
            # Store analogies as insights (their native shape).
            # store_insights_node persists these as packet_type="analogical_insight"
            # packets in packet_store — NOT as knowledge_facts SPO triples.
            existing_insights = list(state.get("insights", []))
            for a in analogies:
                existing_insights.append(
                    {
                        "type": "analogical_insight",
                        "source_domain": a.source_domain,
                        "target_domain": a.target_domain,
                        "pattern": a.pattern,
                        "confidence": a.confidence,
                    }
                )
            state["insights"] = existing_insights

            logger.info(
                "substrate_dag.dtb_analogical_enrichment",
                packet_type=packet_type,
                analogies_found=len(analogies),
            )
    except ImportError:
        pass  # DTB not installed
    except Exception as e:
        logger.debug("substrate_dag.dtb_analogical_enrichment_failed", error=str(e))

    return state


# =============================================================================
# Graph Builder
# =============================================================================


def build_substrate_graph() -> StateGraph:
    """
    Build the LangGraph DAG for memory substrate processing with conditional routing.

    Graph structure (v2.1.0 - Neo4j Graph Sync):
        intake_node → reasoning_node → memory_write_node → graph_sync_node → [CONDITIONAL]
                                                                              ├─ do_embed → semantic_embed_node → extract_insights_node
                                                                              └─ skip_embed → extract_insights_node
        extract_insights_node → store_insights_node → world_model_trigger_node → checkpoint_node

    GMP-42: Conditional routing skips semantic_embed_node for low-value content.
    GMP-NEO4J-DAG: graph_sync_node syncs packets to Neo4j knowledge graph.

    Returns:
        Compiled StateGraph
    """
    # Create graph with state schema
    graph = StateGraph(SubstrateGraphState)

    # Add nodes
    graph.add_node("intake_node", intake_node)
    if _DTB_MEMORY_ENABLED:
        graph.add_node("analogical_enrichment_node", analogical_enrichment_node)
    graph.add_node("reasoning_node", reasoning_node)
    graph.add_node("memory_write_node", memory_write_node)
    graph.add_node("graph_sync_node", graph_sync_node)  # GMP-NEO4J-DAG: Neo4j sync
    graph.add_node("semantic_embed_node", semantic_embed_node)
    graph.add_node("extract_insights_node", extract_insights_node)
    graph.add_node("store_insights_node", store_insights_node)
    graph.add_node("world_model_trigger_node", world_model_trigger_node)
    graph.add_node("checkpoint_node", checkpoint_node)

    # Linear edges (entry through memory_write, then graph_sync)
    graph.set_entry_point("intake_node")
    if _DTB_MEMORY_ENABLED:
        graph.add_edge("intake_node", "analogical_enrichment_node")
        graph.add_edge("analogical_enrichment_node", "reasoning_node")
    else:
        graph.add_edge("intake_node", "reasoning_node")
    graph.add_edge("reasoning_node", "memory_write_node")
    graph.add_edge("memory_write_node", "graph_sync_node")  # GMP-NEO4J-DAG: Neo4j sync

    # CONDITIONAL: Route after graph_sync based on content (GMP-42)
    graph.add_conditional_edges(
        "graph_sync_node",  # Changed from memory_write_node (GMP-NEO4J-DAG)
        route_after_memory_write,
        {
            "do_embed": "semantic_embed_node",
            "skip_embed": "extract_insights_node",
        },
    )

    # Continue from semantic_embed to insights
    graph.add_edge("semantic_embed_node", "extract_insights_node")

    # Rest of pipeline (linear)
    graph.add_edge("extract_insights_node", "store_insights_node")
    graph.add_edge("store_insights_node", "world_model_trigger_node")
    graph.add_edge("world_model_trigger_node", "checkpoint_node")
    graph.add_edge("checkpoint_node", END)

    return graph.compile()


def build_enrichment_graph() -> StateGraph:
    """
    Build enrichment-only DAG (skips intake, memory_write, semantic_embed, checkpoint).

    Graph structure:
        reasoning_node → extract_insights_node → store_insights_node → world_model_trigger_node

    Used by SubstrateDAG.enrich() for post-ingestion enrichment of already-persisted packets.

    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(SubstrateGraphState)

    # Add only enrichment nodes
    graph.add_node("reasoning_node", reasoning_node)
    graph.add_node("extract_insights_node", extract_insights_node)
    graph.add_node("store_insights_node", store_insights_node)
    graph.add_node("world_model_trigger_node", world_model_trigger_node)

    # Linear enrichment pipeline
    graph.set_entry_point("reasoning_node")
    graph.add_edge("reasoning_node", "extract_insights_node")
    graph.add_edge("extract_insights_node", "store_insights_node")
    graph.add_edge("store_insights_node", "world_model_trigger_node")
    graph.add_edge("world_model_trigger_node", END)

    return graph.compile()


# =============================================================================
# Execution Interface
# =============================================================================


class SubstrateDAG:
    """
    Wrapper for executing the substrate DAG with injected dependencies.
    """

    def __init__(
        self, repository=None, semantic_service=None, world_model_service=None
    ):
        """
        Initialize DAG with dependencies.

        Args:
            repository: SubstrateRepository instance
            semantic_service: SemanticService instance
            world_model_service: WorldModelService instance (optional, DB-backed)
        """
        self._repository = repository
        self._semantic_service = semantic_service
        self._world_model_service = world_model_service
        self._graph = build_substrate_graph()
        self._enrichment_graph = build_enrichment_graph()

    @must_stay_async("callers use await")
    async def run(self, envelope: PacketEnvelope) -> PacketWriteResult:
        """
        Run the substrate DAG using native LangGraph execution.

        Uses graph.ainvoke() with config-based dependency injection for all nodes.
        Conditional routing (GMP-42) skips semantic_embed_node for low-value content.

        Args:
            envelope: PacketEnvelope to process

        Returns:
            PacketWriteResult with status and written tables
        """
        # Validate envelope shape before invoke
        if not isinstance(envelope, PacketEnvelope):
            raise ValueError(f"envelope must be PacketEnvelope, got {type(envelope)}")

        # Prepare initial state (v2.0.0 - Native LangGraph Execution)
        initial_state: SubstrateGraphState = {
            "envelope": envelope.model_dump(mode="json"),
            "reasoning_block": None,
            "written_tables": [],
            "embedding_id": None,
            "saved_checkpoint_id": None,
            "insights": [],
            "facts": [],
            "world_model_triggered": False,
            "errors": [],
        }

        # Validate state shape
        if not isinstance(initial_state["envelope"], dict):
            raise ValueError("envelope must serialize to dict")

        # Config with dependencies for all nodes (RunnableConfig pattern)
        config: RunnableConfig = {
            "configurable": {
                "repository": self._repository,
                "semantic_service": self._semantic_service,
                "world_model_service": self._world_model_service,
            }
        }

        # Native LangGraph execution with structured error handling
        try:
            final_state = await asyncio.wait_for(
                self._graph.ainvoke(initial_state, config=config),
                timeout=60.0,  # 60 second timeout for DAG execution
            )
        except TimeoutError:
            logger.error(f"DAG execution timed out for packet {envelope.packet_id}")
            return PacketWriteResult(
                packet_id=envelope.packet_id,
                written_tables=[],
                status="error",
                error_message="DAG execution timeout (60s)",
            )
        except ValueError as e:
            if "configurable" in str(e).lower():
                logger.error(f"Missing dependency in config: {e}")
            raise
        except Exception as e:
            logger.error(f"DAG execution failed: {e}", exc_info=True)
            return PacketWriteResult(
                packet_id=envelope.packet_id,
                written_tables=[],
                status="error",
                error_message=str(e),
            )

        # Build result from final state
        errors = final_state.get("errors", [])
        if errors:
            return PacketWriteResult(
                packet_id=envelope.packet_id,
                written_tables=final_state.get("written_tables", []),
                status="error",
                error_message="; ".join(errors),
            )

        return PacketWriteResult(
            packet_id=envelope.packet_id,
            written_tables=final_state.get("written_tables", []),
            status="ok",
        )

    @must_stay_async("callers use await")
    async def enrich(
        self,
        envelope: PacketEnvelope,
        preload_state: dict[str, Any] | None = None,
    ) -> EnrichmentResult:
        """
        Run ENRICHMENT ONLY pipeline using native LangGraph execution (v2.1.0 - GMP-67).

        SKIPS: intake_node, memory_write_node, semantic_embed_node (already done by core write path)
        RUNS: reasoning_node → extract_insights_node → store_insights_node → world_model_trigger_node

        Pre-validation: Envelope must have packet_id, packet_type, payload populated.
        State is pre-hydrated from envelope (no DB reads required).

        This method is designed to be called AFTER the core write path has
        completed core writes (packet_store, embeddings, neo4j sync).

        Args:
            envelope: Already-persisted PacketEnvelope
            preload_state: Optional pre-hydrated state (for testing or custom workflows)

        Returns:
            EnrichmentResult with extracted facts, insights, and metrics

        Raises:
            ValueError: If envelope is missing required fields
        """
        import time

        start_time = time.time()

        # Pre-validation: envelope must be fully populated
        if not envelope.packet_id:
            raise ValueError("Envelope must have packet_id (already persisted)")
        if not envelope.packet_type:
            raise ValueError("Envelope must have packet_type")
        if not envelope.payload:
            raise ValueError("Envelope must have payload")

        # Pre-hydrate state from envelope (skip intake_node's validation)
        # State matches SubstrateGraphState TypedDict structure
        initial_state: SubstrateGraphState = preload_state or {
            "envelope": envelope.model_dump(mode="json"),
            "reasoning_block": None,
            "written_tables": [],  # Not writing core tables
            "embedding_id": None,  # Already embedded by core write path
            "saved_checkpoint_id": None,
            "insights": [],
            "facts": [],
            "world_model_triggered": False,
            "errors": [],
        }

        # Config with dependencies for all nodes (RunnableConfig pattern)
        config: RunnableConfig = {
            "configurable": {
                "repository": self._repository,
                "semantic_service": self._semantic_service,
                "world_model_service": self._world_model_service,
            }
        }

        # Native LangGraph execution for enrichment
        try:
            final_state = await asyncio.wait_for(
                self._enrichment_graph.ainvoke(initial_state, config=config),
                timeout=30.0,  # 30 second timeout for enrichment
            )
        except TimeoutError:
            logger.error(f"Enrichment timed out for packet {envelope.packet_id}")
            raise
        except Exception as e:
            logger.error(f"Enrichment failed: {e}", exc_info=True)
            raise

        # Build EnrichmentResult
        duration_ms = (time.time() - start_time) * 1000

        # Convert dicts back to typed models
        facts = [
            KnowledgeFact(**f) if isinstance(f, dict) else f
            for f in final_state.get("facts", [])
        ]
        insights = [
            ExtractedInsight(**i) if isinstance(i, dict) else i
            for i in final_state.get("insights", [])
        ]
        reasoning_block = final_state.get("reasoning_block")
        reasoning_trace = (
            StructuredReasoningBlock(**reasoning_block)
            if reasoning_block and isinstance(reasoning_block, dict)
            else reasoning_block
        )

        logger.info(
            "DAG enrichment completed (native execution)",
            packet_id=str(envelope.packet_id),
            facts_count=len(facts),
            insights_count=len(insights),
            world_model_triggered=final_state.get("world_model_triggered", False),
            duration_ms=duration_ms,
        )

        return EnrichmentResult(
            packet_id=envelope.packet_id,
            facts=facts,
            insights=insights,
            reasoning_trace=reasoning_trace,
            facts_inserted=len(facts),
            world_model_triggered=final_state.get("world_model_triggered", False),
            enrichment_duration_ms=duration_ms,
        )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-042",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.schemas", "memory.substrate_models"],
    "tags": [
        "async",
        "debugging",
        "event-driven",
        "learning",
        "llm",
        "logging",
        "memory-substrate",
        "messaging",
        "metrics",
        "rest-api",
    ],
    "keywords": [
        "(ingestion",
        "after",
        "build",
        "checkpoint",
        "dag",
        "embed",
        "enrich",
        "enrichment",
    ],
    "business_value": "intake_node → reasoning_node → memory_write_node → graph_sync_node → semantic_embed_node → checkpoint_node",
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
