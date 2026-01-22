"""  
L9 Memory Substrate - LangGraph DAG
Version: 1.2.0

Implements the substrate processing pipeline as a LangGraph DAG with native execution:
  intake_node → reasoning_node → memory_write_node → [conditional] → semantic_embed_node
                                                                   ↘ extract_insights_node

The DAG routes PacketEnvelopes through processing stages with:
- Native LangGraph execution (graph.ainvoke)
- Conditional routing based on packet content
- Dependency injection via config parameter
- Duplicate packet detection

# bound to memory-yaml2.0 structural layer (NOTE: YAML specifies Neo4j backend, but current implementation uses LangGraph DAG for entity_graph/relationship_traversal/event_timeline)
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph, END

from memory.substrate_models import (
    PacketEnvelope,
    PacketWriteResult,
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
    if len(text_stripped) < 10:
        return True

    return False


# =============================================================================
# State Definition
# =============================================================================


class SubstrateGraphState(TypedDict):
    """
    State passed through the LangGraph DAG.

    Accumulates results from each processing node.
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


async def intake_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Entry node: validates and normalizes the PacketEnvelope.

    - Validates required fields
    - Ensures packet_id and timestamp are set
    - Prepares state for downstream processing
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
    logger.debug("intake_node: Processing packet")

    envelope = state.get("envelope", {})
    errors = list(state.get("errors", []))

    # Validate required fields
    if not envelope.get("packet_type"):
        errors.append("Missing required field: packet_type")
    if not envelope.get("payload"):
        errors.append("Missing required field: payload")
    
    # Check for duplicate packet (if packet_id is provided)
    packet_id = envelope.get("packet_id")
    if packet_id and repository:
        try:
            # Check if packet already exists
            # Note: This requires repository to have a check_packet_exists method
            # For now, we'll skip this check if the method doesn't exist
            if hasattr(repository, "check_packet_exists"):
                exists = await repository.check_packet_exists(packet_id)
                if exists:
                    errors.append(f"Duplicate packet: {packet_id} already processed")
                    logger.warning(f"intake_node: Duplicate packet detected: {packet_id}")
        except Exception as e:
            logger.warning(f"intake_node: Failed to check for duplicate: {e}")

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

    logger.debug(f"intake_node: Processed packet {envelope.get('packet_id')}")

    return {
        **state,
        "envelope": envelope,
        "errors": errors,
    }


async def reasoning_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Reasoning node: generates StructuredReasoningBlock from packet.

    - Extracts features from payload
    - Records inference steps
    - Generates confidence scores
    - Determines memory write operations
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
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
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Memory write node: persists packet and reasoning to database.

    Writes to:
    - packet_store
    - agent_memory_events
    - reasoning_traces (if reasoning block present)
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
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
        errors.append(f"memory_write_node error: {str(e)}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


async def semantic_embed_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Semantic embedding node: generates and stores embedding for payload.

    Only embeds if payload contains text content suitable for semantic search.
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    semantic_service = config.get("configurable", {}).get("semantic_service") if config else None
    
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
        agent_id = envelope.get("metadata", {}).get("agent")
        embedding_id = await semantic_service.embed_and_store(
            text=text_to_embed,
            payload={
                "packet_id": envelope.get("packet_id"),
                "packet_type": packet_type,
                "source_payload": payload,
            },
            agent_id=agent_id,
        )
        written_tables.append("semantic_memory")
        logger.debug(f"semantic_embed_node: Created embedding {embedding_id}")

    except Exception as e:
        logger.error(f"semantic_embed_node: Embedding failed: {e}")
        errors.append(f"semantic_embed_node error: {str(e)}")

    return {
        **state,
        "embedding_id": embedding_id,
        "written_tables": written_tables,
        "errors": errors,
    }


async def checkpoint_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Checkpoint node: saves graph state for recovery.

    Final node in the DAG - persists state to graph_checkpoints.
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
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
        errors.append(f"checkpoint_node error: {str(e)}")

    return {
        **state,
        "saved_checkpoint_id": str(checkpoint_id) if checkpoint_id else None,
        "written_tables": written_tables,
        "errors": errors,
    }


# =============================================================================
# Insight Extraction Nodes (v1.1.0+)
# =============================================================================


async def extract_insights_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Extract insights from packet payload and reasoning block.

    Uses heuristic pattern matching (no ML) to identify:
    - Key-value pairs that look like facts
    - Conclusion-like statements in text
    - Entity mentions and relationships
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
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

        fact = {
            "fact_id": str(uuid4()),
            "subject": payload.get(
                "subject", payload.get("entity", payload.get("name", packet_type))
            ),
            "predicate": key,
            "object": value,
            "confidence": 0.8,
            "source_packet": packet_id,
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
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Store extracted insights and facts to database.

    Persists:
    - KnowledgeFacts to knowledge_facts table
    - Insights as specialized packets
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    
    logger.debug("store_insights_node: Storing insights and facts")

    insights = state.get("insights", [])
    facts = state.get("facts", [])
    errors = list(state.get("errors", []))
    written_tables = list(state.get("written_tables", []))

    if not insights and not facts:
        logger.debug("store_insights_node: No insights or facts to store")
        return state

    if repository is None:
        logger.warning("store_insights_node: No repository, skipping persistence")
        return state

    try:
        # Store facts
        for fact in facts:
            await repository.insert_knowledge_fact(
                fact_id=fact.get("fact_id"),
                subject=fact.get("subject"),
                predicate=fact.get("predicate"),
                object_value=fact.get("object"),
                confidence=fact.get("confidence"),
                source_packet=fact.get("source_packet"),
            )

        if facts:
            written_tables.append("knowledge_facts")
            logger.debug(f"store_insights_node: Stored {len(facts)} facts")

    except Exception as e:
        logger.error(f"store_insights_node: Failed to store: {e}")
        errors.append(f"store_insights_node error: {str(e)}")

    return {
        **state,
        "written_tables": written_tables,
        "errors": errors,
    }


async def world_model_trigger_node(
    state: SubstrateGraphState, config: dict[str, Any] | None = None
) -> SubstrateGraphState:
    """
    Trigger world model update based on extracted insights.

    Calls WorldModelService.update_from_insights() if any
    insight has trigger_world_model=True.

    Integration:
    - Uses world_model.service.WorldModelService for DB-backed updates
    - Falls back to orchestrator if service not available
    """
    # Extract dependencies from config
    repository = config.get("configurable", {}).get("repository") if config else None
    world_model_service = config.get("configurable", {}).get("world_model_service") if config else None
    
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
        errors.append(f"world_model_trigger_node error: {str(e)}")
        return {
            **state,
            "world_model_triggered": False,
            "errors": errors,
        }


# =============================================================================
# Conditional Routing Functions
# =============================================================================


def should_embed_content(state: SubstrateGraphState) -> str:
    """
    Determine if semantic embedding should be performed.
    
    Returns:
        "embed" if content should be embedded, "skip_embed" otherwise
    """
    envelope = state.get("envelope", {})
    packet_type = envelope.get("packet_type", "")
    payload = envelope.get("payload", {})
    
    # Check if packet type or payload suggests semantic content
    should_embed = (
        "semantic" in packet_type.lower()
        or "memory" in packet_type.lower()
        or "text" in payload
        or "content" in payload
        or "description" in payload
    )
    
    # Also check if content would be skipped by embedding filter
    if should_embed:
        text_content = (
            payload.get("text") 
            or payload.get("content") 
            or payload.get("description") 
            or ""
        )
        if _should_skip_embedding(str(text_content)):
            should_embed = False
    
    return "embed" if should_embed else "skip_embed"


# =============================================================================
# Graph Builder
# =============================================================================


def build_substrate_graph() -> StateGraph:
    """
    Build the LangGraph DAG for memory substrate processing.

    Graph structure (v1.1.0+):
        intake_node → reasoning_node → memory_write_node → extract_insights_node
                                    ↘ semantic_embed_node ↗            ↓
                                                          store_insights_node → world_model_trigger_node → checkpoint_node

    Returns:
        Compiled StateGraph
    """
    # Create graph with state schema
    graph = StateGraph(SubstrateGraphState)

    # Add nodes
    graph.add_node("intake_node", intake_node)
    graph.add_node("reasoning_node", reasoning_node)
    graph.add_node("memory_write_node", memory_write_node)
    graph.add_node("semantic_embed_node", semantic_embed_node)
    graph.add_node("extract_insights_node", extract_insights_node)
    graph.add_node("store_insights_node", store_insights_node)
    graph.add_node("world_model_trigger_node", world_model_trigger_node)
    graph.add_node("checkpoint_node", checkpoint_node)

    # Add edges (v1.2.0 with conditional routing)
    graph.set_entry_point("intake_node")
    graph.add_edge("intake_node", "reasoning_node")
    graph.add_edge("reasoning_node", "memory_write_node")
    
    # Conditional routing: only embed if content is suitable
    graph.add_conditional_edges(
        "memory_write_node",
        should_embed_content,
        {
            "embed": "semantic_embed_node",
            "skip_embed": "extract_insights_node",
        }
    )
    
    graph.add_edge("semantic_embed_node", "extract_insights_node")
    graph.add_edge("extract_insights_node", "store_insights_node")
    graph.add_edge("store_insights_node", "world_model_trigger_node")
    graph.add_edge("world_model_trigger_node", "checkpoint_node")
    graph.add_edge("checkpoint_node", END)

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

    async def run(self, envelope: PacketEnvelope) -> PacketWriteResult:
        """
        Run the substrate DAG for a PacketEnvelope.

        Args:
            envelope: PacketEnvelope to process

        Returns:
            PacketWriteResult with status and written tables
        """
        # Prepare initial state (v1.1.0+ with insights)
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

        # Prepare config with dependencies for LangGraph
        config = {
            "configurable": {
                "repository": self._repository,
                "semantic_service": self._semantic_service,
                "world_model_service": self._world_model_service,
            }
        }

        # Use LangGraph to execute the graph natively
        try:
            final_state = await self._graph.ainvoke(initial_state, config=config)
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
