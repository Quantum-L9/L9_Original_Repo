"""
L9 Memory - State Manager
Version: 1.1.0

Thin abstraction over MemorySubstrateService for LangGraph and higher-level
agents that need to load/save state + append events without touching the
repository directly.

Spec v3.0 compliance: Implements state layer responsibilities including
agent_state, long_term_flags, and contradiction_tracking.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "State Manager",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "state_manager",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

import structlog
from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from core.schemas import PacketEnvelopeIn, PacketWriteResult
from memory.substrate_service import MemorySubstrateService
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class MemoryStateManager:
    """
    High-level state manager for agent / graph state.

    Responsibilities:
    - Append PacketEnvelopes to memory (via service.write_packet)
    - Save/load checkpoint state through MemorySubstrateService
    - Provide a clean interface for LangGraph graphs
    """

    def __init__(self, service: MemorySubstrateService, agent_id: str) -> None:
        self._service = service
        self._agent_id = agent_id
        # In-memory flag storage (persisted via checkpoint)
        self._flags: dict[str, Any] = {}
        # In-memory agent state (persisted via checkpoint)
        self._state: dict[str, Any] = {}

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def append_event(
        self,
        packet_type: str,
        payload: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
        provenance: Optional[dict[str, Any]] = None,
        confidence: Optional[dict[str, Any]] = None,
    ) -> PacketWriteResult:
        """
        Append a new event to memory as a PacketEnvelope.

        This is the primary "write" path for agents/graphs.
        """
        packet_in = PacketEnvelopeIn(
            packet_type=packet_type,
            payload=payload,
            metadata=metadata,
            provenance=provenance,
            confidence=confidence,
        )
        return await self._service.write_packet(packet_in)

    async def save_checkpoint(self, state: dict[str, Any]) -> None:
        """
        Save the current graph/agent state as a checkpoint.

        Delegates to MemorySubstrateService.save_checkpoint.
        """
        await self._service.save_checkpoint(agent_id=self._agent_id, state=state)

    async def load_checkpoint(self) -> Optional[dict[str, Any]]:
        """
        Load the latest checkpoint for this agent.

        Delegates to MemorySubstrateService.get_checkpoint.
        """
        return await self._service.get_checkpoint(agent_id=self._agent_id)

    @must_stay_async("callers use await")
    async def start_new_thread(self) -> UUID:
        """
        Generate a new thread_id for multi-turn conversations / graphs.

        This does not write anything by itself; it's a convenience helper.
        """
        return uuid4()

    async def log_trace_step(
        self,
        thread_id: UUID,
        step_name: str,
        thoughts: str,
        extra: Optional[dict[str, Any]] = None,
    ) -> PacketWriteResult:
        """
        Convenience helper for logging a single reasoning trace step.
        """
        payload: dict[str, Any] = {
            "thread_id": str(thread_id),
            "step_name": step_name,
            "thoughts": thoughts,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if extra:
            payload["extra"] = extra

        return await self.append_event(
            packet_type="reasoning_trace",
            payload=payload,
        )

    # =========================================================================
    # Spec v3.0 Required Methods - Agent State
    # =========================================================================

    async def get_agent_flags(self) -> dict[str, Any]:
        """
        Get all flags for the current agent.

        Spec: state.agent_state.get_agent_flags

        Returns:
            Dict of flag_name → value
        """
        # Try to load from checkpoint if flags are empty
        if not self._flags:
            checkpoint = await self.load_checkpoint()
            if checkpoint and "_flags" in checkpoint:
                self._flags = checkpoint["_flags"]
        return self._flags.copy()

    async def update_agent_state(self, patch: dict[str, Any]) -> None:
        """
        Update agent state with a partial patch.

        Spec: state.agent_state.update_agent_state

        Args:
            patch: Dict of state keys to update
        """
        self._state.update(patch)
        # Persist to checkpoint
        await self._persist_state()
        logger.debug(f"Updated agent state: {list(patch.keys())}")

    async def reset_agent_state(self, preserve: Optional[list[str]] = None) -> None:
        """
        Reset agent state, optionally preserving specific keys.

        Spec: state.agent_state.reset_agent_state

        Args:
            preserve: List of state keys to preserve (optional)
        """
        if preserve:
            preserved = {k: self._state[k] for k in preserve if k in self._state}
            self._state = preserved
        else:
            self._state = {}
        await self._persist_state()
        logger.debug(f"Reset agent state, preserved: {preserve or []}")

    # =========================================================================
    # Spec v3.0 Required Methods - Long-term Flags
    # =========================================================================

    async def set_flag(
        self,
        flag_name: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set a long-term flag for the agent.

        Spec: state.long_term_flags.set_flag

        Args:
            flag_name: Name of the flag
            value: Value to set
            ttl: Optional TTL in seconds (not implemented in hybrid mode)
        """
        self._flags[flag_name] = {
            "value": value,
            "set_at": datetime.utcnow().isoformat(),
            "ttl": ttl,
        }
        await self._persist_state()
        logger.debug(f"Set flag: {flag_name}")

    async def get_flag(self, flag_name: str) -> Any:
        """
        Get a flag value.

        Spec: state.long_term_flags.get_flag

        Args:
            flag_name: Name of the flag

        Returns:
            Flag value or None if not set
        """
        # Ensure flags are loaded
        await self.get_agent_flags()
        flag_data = self._flags.get(flag_name)
        if flag_data is None:
            return None
        return flag_data.get("value") if isinstance(flag_data, dict) else flag_data

    async def delete_flag(self, flag_name: str) -> None:
        """
        Delete a flag.

        Spec: state.long_term_flags.delete_flag

        Args:
            flag_name: Name of the flag to delete
        """
        if flag_name in self._flags:
            del self._flags[flag_name]
            await self._persist_state()
            logger.debug(f"Deleted flag: {flag_name}")

    # =========================================================================
    # Spec v3.0 Required Methods - Contradiction Tracking
    # =========================================================================

    async def record_contradiction(
        self,
        subject: str,
        predicate: str,
        conflicting_objects: list[Any],
        source_packet: Optional[UUID] = None,
    ) -> None:
        """
        Record a contradiction between facts.

        Spec: state.contradiction_tracking.record_contradiction

        Args:
            subject: Subject of the contradicting facts
            predicate: Predicate of the contradicting facts
            conflicting_objects: List of conflicting values
            source_packet: Optional source packet UUID
        """
        # Log as event packet
        await self.append_event(
            packet_type="contradiction_detected",
            payload={
                "subject": subject,
                "predicate": predicate,
                "conflicting_objects": conflicting_objects,
                "detected_at": datetime.utcnow().isoformat(),
            },
            metadata={"source_packet": str(source_packet) if source_packet else None},
        )
        logger.warning(
            f"Contradiction recorded: {subject}.{predicate} has {len(conflicting_objects)} conflicting values"
        )

    async def get_contradiction_count(self, subject: str, predicate: str) -> int:
        """
        Get contradiction count for a subject-predicate pair.

        Spec: state.contradiction_tracking.get_contradiction_count

        Note: This is a simplified implementation that counts via repository.
        For full implementation, would track per subject-predicate.

        Args:
            subject: Subject
            predicate: Predicate

        Returns:
            Number of contradictions recorded
        """
        # Get facts and sum contradiction counts
        repo = self._service._repository
        if repo is None:
            return 0

        facts = await repo.get_facts_by_subject(subject)
        return sum(
            getattr(f, "contradiction_count", 0)
            for f in facts
            if f.predicate == predicate
        )

    async def resolve_contradiction(
        self,
        fact_id: UUID,
        resolution: str,
        resolved_by: str,
    ) -> None:
        """
        Resolve a contradiction by deprecating a fact.

        Spec: state.contradiction_tracking.resolve_contradiction

        Args:
            fact_id: UUID of the fact to deprecate
            resolution: Resolution description
            resolved_by: Who/what resolved it
        """
        repo = self._service._repository
        if repo is None:
            logger.warning("No repository available for contradiction resolution")
            return

        reason = f"Resolved by {resolved_by}: {resolution}"
        success = await repo.deprecate_fact(fact_id, reason)

        if success:
            logger.info(f"Contradiction resolved: fact {fact_id} deprecated")
        else:
            logger.warning(f"Failed to resolve contradiction: fact {fact_id} not found")

    async def get_active_facts(
        self,
        subject: str,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Get active (non-deprecated) facts for a subject.

        Spec: state.contradiction_tracking.get_active_facts

        Args:
            subject: Subject to get facts for
            min_confidence: Minimum confidence threshold

        Returns:
            List of active facts as dicts
        """
        repo = self._service._repository
        if repo is None:
            return []

        facts = await repo.get_active_facts(subject, min_confidence)
        return [
            {
                "fact_id": str(f.fact_id),
                "subject": f.subject,
                "predicate": f.predicate,
                "object": f.object,
                "confidence": f.confidence,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in facts
        ]

    async def deprecate_fact(self, fact_id: UUID, reason: str) -> None:
        """
        Deprecate a fact.

        Spec: state.contradiction_tracking.deprecate_fact

        Args:
            fact_id: UUID of fact to deprecate
            reason: Reason for deprecation
        """
        repo = self._service._repository
        if repo is None:
            logger.warning("No repository available for fact deprecation")
            return

        success = await repo.deprecate_fact(fact_id, reason)
        if success:
            logger.info(f"Fact deprecated: {fact_id}")
        else:
            logger.warning(f"Failed to deprecate fact: {fact_id}")

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _persist_state(self) -> None:
        """Persist flags and state to checkpoint."""
        checkpoint_data = {
            "_flags": self._flags,
            "_state": self._state,
            "_persisted_at": datetime.utcnow().isoformat(),
        }
        await self.save_checkpoint(checkpoint_data)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-007",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.schemas", "memory.substrate_service"],
    "tags": ["async", "debugging", "event-driven", "learning", "logging", "memory-substrate", "service", "testing", "tracing"],
    "keywords": ["active", "agent", "append", "checkpoint", "compliance", "contradiction", "count", "delete"],
    "business_value": "Implements MemoryStateManager for state manager functionality",
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
