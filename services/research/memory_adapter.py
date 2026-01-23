"""
L9 Research Factory - Memory Substrate Adapter
Version: 1.0.0

Adapter to integrate Research Factory with L9 Memory Substrate.
Maps ResearchGraphState to PacketEnvelope and writes to substrate tables.

NO NEW TABLES - uses only existing substrate tables:
- packet_store
- reasoning_traces
- agent_memory_events
- graph_checkpoints
- semantic_memory
- agent_log
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Substrate Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T13:21:46Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "memory_adapter",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "core.singleton_registry",
            "services.research.__init__",
            "services.research.graph_runtime",
            "services.research.research_graph",
            "tests.test_memory_adapter",
        ],
    },
}
# ============================================================================

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

from core.schemas import (PacketConfidence, PacketEnvelope, PacketMetadata,
                          PacketProvenance)
from core.singleton_auto_registry import register_singleton
from memory.substrate_models import StructuredReasoningBlock
from memory.substrate_repository import SubstrateRepository, get_repository
from services.research.graph_state import ResearchGraphState

logger = structlog.get_logger(__name__)


class ResearchMemoryAdapter:
    """
    Adapter between Research Factory and Memory Substrate.

    Responsibilities:
    - Convert ResearchGraphState to PacketEnvelope for persistence
    - Save/load graph checkpoints
    - Log agent memory events
    - Store reasoning traces
    """

    def __init__(self, repository: Optional[SubstrateRepository] = None):
        """
        Initialize adapter with optional repository.

        Args:
            repository: SubstrateRepository instance. If None, uses singleton.
        """
        self._repository = repository

    @property
    def repository(self) -> SubstrateRepository:
        """Get the repository instance."""
        if self._repository is None:
            self._repository = get_repository()
        return self._repository

    # =========================================================================
    # State ↔ PacketEnvelope Conversion
    # =========================================================================

    def state_to_envelope(
        self,
        state: ResearchGraphState,
        packet_type: str = "research_state",
        agent_id: str = "research_graph",
    ) -> PacketEnvelope:
        """
        Convert ResearchGraphState to PacketEnvelope for substrate storage.

        Args:
            state: The research graph state
            packet_type: Type of packet (e.g., 'research_state', 'research_step')
            agent_id: Agent identifier for tracking

        Returns:
            PacketEnvelope ready for substrate insertion
        """
        # Convert state to JSON-serializable dict
        payload = dict(state)

        # Create envelope
        envelope = PacketEnvelope(
            packet_id=uuid4(),
            packet_type=packet_type,
            timestamp=datetime.utcnow(),
            payload=payload,
            metadata=PacketMetadata(
                schema_version="1.0.0",
                reasoning_mode="multi_agent",
                agent=agent_id,
                domain="research",
            ),
            provenance=PacketProvenance(
                source="research_factory",
                tool=None,
                parent_packet=(
                    UUID(state["packet_id"]) if state.get("packet_id") else None
                ),
            ),
            confidence=(
                PacketConfidence(
                    score=state.get("critic_score", 0.0),
                    rationale=state.get("critic_feedback", ""),
                )
                if state.get("critic_score")
                else None
            ),
        )

        return envelope

    def envelope_to_state(self, envelope: PacketEnvelope) -> ResearchGraphState:
        """
        Convert PacketEnvelope back to ResearchGraphState.

        Args:
            envelope: The packet envelope from substrate

        Returns:
            Reconstructed ResearchGraphState
        """
        payload = envelope.payload

        # Reconstruct state from payload
        state = ResearchGraphState(
            thread_id=payload.get("thread_id", ""),
            request_id=payload.get("request_id", ""),
            user_id=payload.get("user_id", "anonymous"),
            original_query=payload.get("original_query", ""),
            refined_goal=payload.get("refined_goal", ""),
            plan=payload.get("plan", []),
            current_step_idx=payload.get("current_step_idx", 0),
            evidence=payload.get("evidence", []),
            sources=payload.get("sources", []),
            swarm_results=payload.get("swarm_results", []),
            critic_score=payload.get("critic_score", 0.0),
            critic_feedback=payload.get("critic_feedback", ""),
            retry_count=payload.get("retry_count", 0),
            final_summary=payload.get("final_summary", ""),
            final_output=payload.get("final_output", {}),
            errors=payload.get("errors", []),
            timestamp=payload.get("timestamp", datetime.utcnow().isoformat()),
            packet_id=str(envelope.packet_id),
        )

        return state

    # =========================================================================
    # Checkpoint Operations (uses graph_checkpoints table)
    # =========================================================================

    async def save_checkpoint(
        self,
        state: ResearchGraphState,
        agent_id: str = "research_graph",
    ) -> UUID:
        """
        Save research graph state as checkpoint.

        Uses the substrate's graph_checkpoints table with agent_id as key.

        Args:
            state: Current graph state
            agent_id: Agent/thread identifier for checkpoint lookup

        Returns:
            Checkpoint ID
        """
        # Convert state to dict for storage
        graph_state = dict(state)

        # Use thread_id as unique key for this research session
        checkpoint_key = f"{agent_id}:{state['thread_id']}"

        checkpoint_id = await self.repository.save_checkpoint(
            agent_id=checkpoint_key,
            graph_state=graph_state,
        )

        logger.debug(f"Saved checkpoint {checkpoint_id} for {checkpoint_key}")
        return checkpoint_id

    async def load_checkpoint(
        self,
        thread_id: str,
        agent_id: str = "research_graph",
    ) -> Optional[ResearchGraphState]:
        """
        Load research graph state from checkpoint.

        Args:
            thread_id: Thread/session ID to load
            agent_id: Agent identifier

        Returns:
            ResearchGraphState if found, None otherwise
        """
        checkpoint_key = f"{agent_id}:{thread_id}"

        checkpoint = await self.repository.get_checkpoint(agent_id=checkpoint_key)

        if checkpoint:
            logger.debug(f"Loaded checkpoint for {checkpoint_key}")
            # Reconstruct state from graph_state field
            return ResearchGraphState(**checkpoint.graph_state)

        return None

    # =========================================================================
    # Memory Event Operations (uses agent_memory_events table)
    # =========================================================================

    async def log_memory_event(
        self,
        agent_id: str,
        event_type: str,
        content: dict[str, Any],
        packet_id: Optional[UUID] = None,
    ) -> UUID:
        """
        Log a memory event for an agent.

        Uses agent_memory_events table.

        Args:
            agent_id: Agent identifier
            event_type: Type of event (e.g., 'planning_started', 'research_completed')
            content: Event content/payload
            packet_id: Optional associated packet ID

        Returns:
            Event ID
        """
        event_id = await self.repository.insert_memory_event(
            agent_id=agent_id,
            event_type=event_type,
            content=content,
            packet_id=packet_id,
        )

        logger.debug(f"Logged memory event {event_id} for {agent_id}: {event_type}")
        return event_id

    # =========================================================================
    # Reasoning Trace Operations (uses reasoning_traces table)
    # =========================================================================

    async def save_reasoning_trace(
        self,
        agent_id: str,
        packet_id: UUID,
        reasoning_steps: list[str],
        features: dict[str, Any],
        confidence: float,
    ) -> UUID:
        """
        Save a reasoning trace for an agent action.

        Uses reasoning_traces table.

        Args:
            agent_id: Agent that performed reasoning
            packet_id: Associated packet ID
            reasoning_steps: Step-by-step reasoning
            features: Extracted features/observations
            confidence: Overall confidence score

        Returns:
            Trace ID
        """
        block = StructuredReasoningBlock(
            block_id=uuid4(),
            packet_id=packet_id,
            extracted_features=features,
            inference_steps=[{"step": s} for s in reasoning_steps],
            reasoning_tokens=reasoning_steps,
            decision_tokens=[],
            confidence_scores={"overall": confidence},
            memory_write_ops=[],
            timestamp=datetime.utcnow(),
        )

        # Add agent_id as attribute for repository
        block.agent_id = agent_id  # type: ignore

        trace_id = await self.repository.insert_reasoning_block(block)

        logger.debug(f"Saved reasoning trace {trace_id} for {agent_id}")
        return trace_id

    # =========================================================================
    # Packet Store Operations (uses packet_store table)
    # =========================================================================

    async def save_state_as_packet(
        self,
        state: ResearchGraphState,
        packet_type: str = "research_state",
        agent_id: str = "research_graph",
    ) -> UUID:
        """
        Save state as a packet in packet_store.

        Args:
            state: Research graph state
            packet_type: Packet type classification
            agent_id: Agent identifier

        Returns:
            Packet ID
        """
        envelope = self.state_to_envelope(state, packet_type, agent_id)
        packet_id = await self.repository.insert_packet(envelope)

        logger.debug(f"Saved state as packet {packet_id}")
        return packet_id

    # =========================================================================
    # Agent Log Operations (uses agent_log table)
    # =========================================================================

    async def log(
        self,
        agent_id: str,
        level: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> UUID:
        """
        Write a log entry to agent_log table.

        Args:
            agent_id: Agent identifier
            level: Log level (INFO, WARNING, ERROR)
            message: Log message
            metadata: Optional additional metadata

        Returns:
            Log ID
        """
        log_id = await self.repository.insert_log(
            agent_id=agent_id,
            level=level,
            message=message,
            metadata=metadata,
        )

        return log_id


# Singleton adapter instance
_adapter: Optional[ResearchMemoryAdapter] = None


@register_singleton(
    name="research_memory_adapter",
    lifecycle="lazy",
    description="Research service memory adapter",
)
def get_memory_adapter() -> ResearchMemoryAdapter:
    """Get or create memory adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = ResearchMemoryAdapter()
    return _adapter


def init_memory_adapter(repository: SubstrateRepository) -> ResearchMemoryAdapter:
    """Initialize memory adapter with repository."""
    global _adapter
    _adapter = ResearchMemoryAdapter(repository)
    return _adapter


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.substrate_models",
        "memory.substrate_repository",
    ],
    "tags": [
        "adapter",
        "adapter-pattern",
        "async",
        "debugging",
        "event-driven",
        "logging",
        "messaging",
        "operations",
        "research-services",
        "tracing",
    ],
    "keywords": [
        "adapter",
        "checkpoint",
        "envelope",
        "event",
        "factory",
        "load",
        "log",
        "memory",
    ],
    "business_value": "Implements ResearchMemoryAdapter for memory adapter functionality",
    "last_modified": "2026-01-14T13:21:46Z",
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
