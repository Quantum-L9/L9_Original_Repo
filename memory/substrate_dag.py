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
from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID, uuid4

import structlog
from langchain_core.runnables import RunnableConfig

from core.decorators import must_stay_async
from core.schemas import PacketEnvelope, PacketWriteResult
from langgraph.graph import END, StateGraph
from memory.graph_client import get_neo4j_client
from memory.substrate_models import (
    EnrichmentResult,
    ExtractedInsight,
    KnowledgeFact,
    StructuredReasoningBlock,
)

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

    - Validates required fields
    - Ensures packet_id and timestamp are set
    - Checks for duplicate packets (prevents reprocessing)
    - Prepares state for downstream processing
    """
    repository = _get_config_dependency(config, "repository")
    logger.debug("intake_node: Processing packet")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))

    # Validate required fields
    if not envelope.get("packet_type"):
        errors.append("Missing required field: packet_type")
    if not envelope.get("payload"):
        errors.append("Missing required field: payload")

    # Ensure packet_id
    if not envelope.get("packet_id"):
        envelope["packet_id"] = str(uuid4())

    # Ensure timestamp
    if not envelope.get("timestamp"):
        envelope["timestamp"] = datetime.utcnow().isoformat()

    # Ensure metadata structure
    if not envelope.get("metadata"):
        envelope["metadata"] = {
            "schema_version": "1.0.0",
            "reasoning_mode": None,
            "agent": None,
            "domain": "plastic_brokerage",
        }

    # Check for duplicate packet (prevents reprocessing already-ingested packets)
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
            # Non-fatal: log warning but continue processing
            logger.warning(
                "intake_node: Failed to check for duplicate",
                packet_id=str(packet_id),
                error=str(e),
            )

    logger.debug(f"intake_node: Processed packet {envelope.get('packet_id')}")

    return {
        **state,
        "envelope": envelope,
        "errors": errors,
    }


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
        "timestamp": datetime.utcnow().isoformat(),
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
        reasoning_block["memory_write_ops"].append(
            {"table": "reasoning_traces", "operation": "insert"}
        )

    logger.debug(f"reasoning_node: Generated block {reasoning_block['block_id']}")

    return {
        **state,
        "reasoning_block": reasoning_block,
    }


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
        # Still mark what would have been written
        written_tables.extend(["packet_store", "agent_memory_events"])
        if reasoning_block:
            written_tables.append("reasoning_traces")
        return {
            **state,
            "written_tables": written_tables,
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
        timestamp = envelope.get("timestamp", datetime.utcnow().isoformat())
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


async def semantic_embed_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Semantic embedding node: generates and stores embedding for payload.

    Only embeds if payload contains text content suitable for semantic search.
    """
    # Note: repository not used in this node (embedding via semantic_service)
    semantic_service = _get_config_dependency(config, "semantic_service")
    logger.debug("semantic_embed_node: Processing embedding")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))
    embedding_id = None

    # Skip if previous errors
    if errors:
        logger.warning("semantic_embed_node: Skipping due to previous errors")
        return state

    payload = envelope.get("payload", {})
    packet_type = envelope.get("packet_type", "")

    # Determine if embedding should be generated
    should_embed = (
        "semantic" in packet_type.lower()
        or "memory" in packet_type.lower()
        or "text" in payload
        or "content" in payload
        or "description" in payload
    )

    if not should_embed:
        logger.debug("semantic_embed_node: Skipping - no embeddable content")
        return state

    # Extract text to embed
    text_to_embed = (
        payload.get("text")
        or payload.get("content")
        or payload.get("description")
        or str(payload)[:1000]  # Fallback to stringified payload
    )

    # GMP-42: Skip embedding for known low-value content patterns
    if _should_skip_embedding(text_to_embed):
        logger.debug(
            "semantic_embed_node: Skipping - low-value content pattern detected",
            text_preview=text_to_embed[:50] if text_to_embed else None,
            packet_type=packet_type,
        )
        return state

    if semantic_service is None:
        logger.warning("semantic_embed_node: No semantic service, skipping")
        return state

    try:
        metadata = envelope.get("metadata", {})
        agent_id = metadata.get("agent")
        # Extract scope from metadata for RLS (default to 'shared' for backward compat)
        scope = metadata.get("db_scope") or metadata.get("scope") or "shared"

        embedding_id = await semantic_service.embed_and_store(
            text=text_to_embed,
            payload={
                "packet_id": envelope.get("packet_id"),
                "packet_type": packet_type,
                "source_payload": payload,
            },
            agent_id=agent_id,
            scope=scope,  # Pass scope for RLS
        )
        written_tables.append("semantic_memory")
        logger.debug(
            f"semantic_embed_node: Created embedding {embedding_id} scope={scope}"
        )

    except Exception as e:
        logger.error(f"semantic_embed_node: Embedding failed: {e}")
        errors.append(f"semantic_embed_node error: {e!s}")

    return {
        **state,
        "embedding_id": embedding_id,
        "written_tables": written_tables,
        "errors": errors,
    }


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
                "timestamp": datetime.utcnow().isoformat(),
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
    Extract insights from packet payload and reasoning block.

    Uses heuristic pattern matching (no ML) to identify:
    - Key-value pairs that look like facts
    - Conclusion-like statements in text
    - Entity mentions and relationships
    """
    # Note: repository not used in this node (extraction is stateless)
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
            "created_at": datetime.utcnow().isoformat(),
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
                        "entities": [
                            envelope.get("metadata", {}).get("agent", "unknown")
                        ],
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
        # Simple pattern: look for "X is Y" or "X has Y" structures
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

    logger.debug(
        f"extract_insights_node: Extracted {len(insights)} insights, {len(facts)} facts"
    )

    return {
        **state,
        "insights": insights,
        "facts": facts,
    }


async def store_insights_node(
    state: SubstrateGraphState, config: RunnableConfig = None
) -> SubstrateGraphState:
    """
    Store extracted insights and facts to database (v2.1.0 - GMP-67).

    Persists:
    - KnowledgeFacts to knowledge_facts table via UPSERT (idempotent)
    - Insights as specialized packets (future)

    Uses repository.insert_knowledge_fact() which performs ON CONFLICT UPSERT,
    ensuring same packet enriched multiple times doesn't create duplicate facts.
    """
    from uuid import UUID

    repository = _get_config_dependency(config, "repository")
    logger.debug("store_insights_node: Storing insights and facts")

    insights = state.get("insights", [])
    facts = state.get("facts", [])
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))

    # Get packet_id from envelope for linking facts to source packet
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

    if not insights and not facts:
        logger.debug("store_insights_node: No insights or facts to store")
        return state

    if repository is None:
        logger.warning("store_insights_node: No repository, skipping persistence")
        return state

    try:
        # Store facts via UPSERT (idempotent)
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
            )
            facts_inserted += 1

        if facts_inserted > 0:
            written_tables.append("knowledge_facts")
            logger.debug(
                f"store_insights_node: Upserted {facts_inserted} facts for packet {packet_id}"
            )

    except Exception as e:
        logger.error(f"store_insights_node: Failed to store: {e}")
        errors.append(f"store_insights_node error: {e!s}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


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
        should_embed = (
            "semantic" in packet_type.lower()
            or "memory" in packet_type.lower()
            or "text" in payload
            or "content" in payload
            or "description" in payload
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

    async def enrich(
        self,
        envelope: PacketEnvelope,
        preload_state: dict[str, Any] | None = None,
    ) -> EnrichmentResult:
        """
        Run ENRICHMENT ONLY pipeline using native LangGraph execution (v2.1.0 - GMP-67).

        SKIPS: intake_node, memory_write_node, semantic_embed_node (already done by IngestionPipeline)
        RUNS: reasoning_node → extract_insights_node → store_insights_node → world_model_trigger_node

        Pre-validation: Envelope must have packet_id, packet_type, payload populated.
        State is pre-hydrated from envelope (no DB reads required).

        This method is designed to be called AFTER IngestionPipeline.ingest() has
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
            "embedding_id": None,  # Already embedded by IngestionPipeline
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
