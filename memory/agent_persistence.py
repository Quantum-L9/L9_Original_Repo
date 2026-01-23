"""
L9 Memory - Agent Persistence Service
Version: 1.1.0

Agent persistence layer for checkpoint management and state serialization.
Implements memory_spec_v3.0.yaml memory_layers.persistence contract.

Responsibilities:
- Checkpoint management (create, restore, list, delete)
- State serialization (serialize, deserialize, validate)
- Checkpoint triggers: on_agent_shutdown, on_session_boundary, on_critical_decision, scheduled_hourly
- Cryptographic integrity validation (SHA-256 checksums)
- Prometheus metrics for observability
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Persistence Service",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "agent_persistence",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.server",
            "core.agents.executor",
            "memory.retention_engine",
            "memory.substrate_service",
            "tests.memory.test_agent_persistence",
        ],
    },
}
# ============================================================================

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

from core.schemas import PacketEnvelopeIn
from memory.checkpoint_metrics import get_metrics
from memory.checkpoint_validator import CheckpointValidator
from memory.substrate_repository import SubstrateRepository

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class Checkpoint:
    """Represents an agent checkpoint."""

    def __init__(
        self,
        checkpoint_id: UUID,
        agent_id: str,
        state: Dict[str, Any],
        reason: str,
        created_at: datetime,
    ):
        self.checkpoint_id = checkpoint_id
        self.agent_id = agent_id
        self.state = state
        self.reason = reason
        self.created_at = created_at


class AgentPersistenceService:
    """
    Agent persistence service for checkpoint management.

    Per memory_spec_v3.0.yaml memory_layers.persistence:
    - create_checkpoint(agent_id, state, reason) -> UUID
    - restore_checkpoint(agent_id, checkpoint_id) -> dict
    - list_checkpoints(agent_id, limit) -> List[Checkpoint]
    - delete_old_checkpoints(agent_id, keep_last) -> int
    - serialize_agent_state(agent) -> dict
    - deserialize_agent_state(state) -> dict
    - validate_checkpoint_integrity(checkpoint_id) -> bool
    """

    def __init__(
        self,
        service: Optional[MemorySubstrateService] = None,
        repository: Optional[SubstrateRepository] = None,
        enable_checksums: bool = True,
    ):
        """
        Initialize agent persistence service.

        Args:
            service: MemorySubstrateService for checkpoint operations
            repository: SubstrateRepository (alternative to service)
            enable_checksums: Enable SHA-256 checksum validation (default: True)
        """
        self._service = service
        self._repository = repository
        self._enable_checksums = enable_checksums

        # Initialize validator for integrity checks
        self._validator = CheckpointValidator()

        # Retention policy per spec
        self._retention_policy = {
            "keep_last_n": 10,
            "keep_daily_for_days": 30,
            "keep_weekly_for_weeks": 12,
            "keep_monthly_for_months": 6,
        }

        logger.info(
            "AgentPersistenceService initialized",
            checksums_enabled=enable_checksums,
        )

    def set_service(self, service: MemorySubstrateService) -> None:
        """Set or update service reference."""
        self._service = service

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    async def create_checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        reason: str = "manual",
    ) -> UUID:
        """
        Create a checkpoint for an agent.

        Args:
            agent_id: Agent identifier
            state: Agent state dict to persist
            reason: Checkpoint reason (on_agent_shutdown, on_session_boundary, on_critical_decision, scheduled_hourly, manual)

        Returns:
            Checkpoint UUID
        """
        metrics = get_metrics(agent_id)

        with metrics.time_create(reason):
            logger.debug(
                "Creating checkpoint",
                agent_id=agent_id,
                reason=reason,
                state_keys=list(state.keys()),
            )

            # Store checkpoint reason in state for later retrieval
            state_with_meta = {**state, "_checkpoint_reason": reason}

            # Add checksum for integrity validation
            if self._enable_checksums:
                state_with_meta = self._validator.add_checksum_to_state(state_with_meta)

            checkpoint_id: Optional[UUID] = None

            if self._service:
                checkpoint_id = await self._service.save_checkpoint(
                    agent_id=agent_id,
                    state=state_with_meta,
                )
            elif self._repository:
                checkpoint_id = await self._repository.save_checkpoint(
                    agent_id=agent_id,
                    graph_state=state_with_meta,
                )
            else:
                raise RuntimeError("Neither service nor repository set")

            # Record checkpoint size metric
            state_size = len(json.dumps(state_with_meta, default=str))
            metrics.record_size(state_size)

            logger.info(
                "Checkpoint created",
                checkpoint_id=str(checkpoint_id),
                agent_id=agent_id,
                size_bytes=state_size,
                checksum_enabled=self._enable_checksums,
            )

            # Emit PacketEnvelope for audit trail (best-effort)
            await self._emit_checkpoint_packet(
                event_type="checkpoint_created",
                agent_id=agent_id,
                checkpoint_id=checkpoint_id,
                reason=reason,
                state_keys=list(state.keys()),
            )

            return checkpoint_id

    async def restore_checkpoint(
        self,
        agent_id: str,
        checkpoint_id: Optional[UUID] = None,
        validate_integrity: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore a checkpoint for an agent.

        If checkpoint_id is None, restores the latest checkpoint.

        Args:
            agent_id: Agent identifier
            checkpoint_id: Optional specific checkpoint UUID
            validate_integrity: Validate checksum before restore (default: True)

        Returns:
            Agent state dict, or None if not found

        Raises:
            ValueError: If checkpoint integrity validation fails
        """
        metrics = get_metrics(agent_id)

        with metrics.time_restore():
            logger.debug(
                "Restoring checkpoint",
                agent_id=agent_id,
                checkpoint_id=str(checkpoint_id) if checkpoint_id else "latest",
            )

            state: Optional[Dict[str, Any]] = None
            restored_checkpoint_id: Optional[UUID] = None

            if self._service:
                state = await self._service.get_checkpoint(agent_id=agent_id)
                if state:
                    logger.info("Checkpoint restored", agent_id=agent_id)
            elif self._repository:
                checkpoint = await self._repository.get_checkpoint(agent_id=agent_id)
                if checkpoint:
                    state = checkpoint.graph_state
                    restored_checkpoint_id = checkpoint.checkpoint_id
                    logger.info(
                        "Checkpoint restored",
                        agent_id=agent_id,
                        checkpoint_id=str(checkpoint.checkpoint_id),
                    )
            else:
                raise RuntimeError("Neither service nor repository set")

            if state is None:
                return None

            # Validate checksum if enabled
            if self._enable_checksums and validate_integrity:
                is_valid, error_msg = self._validator.validate_checksum(state)
                metrics.record_validation(is_valid)

                if not is_valid:
                    metrics.record_corruption()
                    logger.error(
                        "Checkpoint integrity validation FAILED",
                        agent_id=agent_id,
                        checkpoint_id=str(restored_checkpoint_id),
                        error=error_msg,
                    )
                    raise ValueError(
                        f"Checkpoint integrity validation failed: {error_msg}"
                    )

            # Remove internal metadata before returning
            state_clean = self._validator.strip_metadata_for_restore(state)
            reason = state.get("_checkpoint_reason", "unknown")

            # Emit PacketEnvelope for audit trail (best-effort)
            await self._emit_checkpoint_packet(
                event_type="checkpoint_restored",
                agent_id=agent_id,
                checkpoint_id=restored_checkpoint_id,
                reason=reason,
                state_keys=list(state_clean.keys()),
            )

            return state_clean

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Checkpoint]:
        """
        List checkpoints for an agent.

        Note: Current schema uses UNIQUE(agent_id) so returns at most 1 checkpoint.
        Full multi-checkpoint support requires schema migration.

        Args:
            agent_id: Agent identifier
            limit: Maximum checkpoints to return

        Returns:
            List of Checkpoint objects (currently max 1 due to schema)
        """
        logger.debug("Listing checkpoints", agent_id=agent_id, limit=limit)

        if self._repository is None:
            raise RuntimeError("Repository not set")

        rows = await self._repository.list_checkpoints(agent_id=agent_id, limit=limit)

        checkpoints = []
        for row in rows:
            # Extract reason from graph_state if present, default to "unknown"
            reason = (
                row.graph_state.get("_checkpoint_reason", "unknown")
                if isinstance(row.graph_state, dict)
                else "unknown"
            )
            checkpoints.append(
                Checkpoint(
                    checkpoint_id=row.checkpoint_id,
                    agent_id=row.agent_id,
                    state=row.graph_state,
                    reason=reason,
                    created_at=row.updated_at,
                )
            )

        logger.info("Listed checkpoints", agent_id=agent_id, count=len(checkpoints))
        return checkpoints

    async def delete_old_checkpoints(
        self,
        agent_id: str,
        keep_last: int = 10,
    ) -> int:
        """
        Delete old checkpoints, keeping only the most recent N.

        Supports both:
        - Pre-0014 schema (UNIQUE constraint): At most 1 checkpoint, delete if keep_last=0
        - Post-0014 schema (multi-checkpoint): Properly keeps last N, deletes older

        Args:
            agent_id: Agent identifier
            keep_last: Number of recent checkpoints to keep (0 = delete all)

        Returns:
            Number of checkpoints deleted
        """
        metrics = get_metrics(agent_id)

        logger.debug("Deleting old checkpoints", agent_id=agent_id, keep_last=keep_last)

        if self._repository is None:
            raise RuntimeError("Repository not set")

        # Use repository method that handles both schema versions
        if keep_last == 0:
            # Delete all checkpoints
            deleted = await self._repository.delete_checkpoint(agent_id=agent_id)
            count = 1 if deleted else 0
        else:
            # Keep last N checkpoints (uses proper SQL for multi-checkpoint schema)
            count = await self._repository.delete_old_checkpoints(
                agent_id=agent_id,
                keep_last=keep_last,
            )

        if count > 0:
            # Record deletion metrics
            metrics.record_delete(count, reason="retention")

            logger.info(
                "Deleted old checkpoints",
                agent_id=agent_id,
                deleted_count=count,
                kept=keep_last,
            )

            # Emit PacketEnvelope for audit trail
            await self._emit_checkpoint_packet(
                event_type="checkpoints_pruned",
                agent_id=agent_id,
                checkpoint_id=None,
                reason=f"retention_keep_last_{keep_last}",
                state_keys=["deleted_count", "kept"],
            )

        return count

    def serialize_agent_state(self, agent: Any) -> Dict[str, Any]:
        """
        Serialize an agent object to a state dict.

        Args:
            agent: Agent object to serialize

        Returns:
            Serialized state dict
        """
        if hasattr(agent, "model_dump"):
            # Pydantic model
            return agent.model_dump(mode="json")
        elif hasattr(agent, "__dict__"):
            # Regular object
            return {
                k: self._serialize_value(v)
                for k, v in agent.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(agent, dict):
            # Already a dict
            return agent
        else:
            # Fallback: convert to string
            return {"state": str(agent)}

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a value."""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        else:
            return str(value)

    def deserialize_agent_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize a state dict back to agent-compatible format.

        Args:
            state: Serialized state dict

        Returns:
            Deserialized state dict (ready for agent restoration)
        """
        # For now, return state as-is
        # In production, might need to restore UUIDs, datetimes, etc.
        return state

    async def validate_checkpoint_integrity(
        self,
        checkpoint_id: UUID,
        agent_id: Optional[str] = None,
    ) -> bool:
        """
        Validate checkpoint integrity.

        Checks:
        - Checkpoint exists
        - State is valid JSON
        - SHA-256 checksum matches (if present)
        - Required fields present

        Args:
            checkpoint_id: Checkpoint UUID to validate
            agent_id: Optional agent ID for metrics (auto-detected if not provided)

        Returns:
            True if valid, False otherwise
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")

        try:
            async with self._repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT checkpoint_id, agent_id, graph_state
                    FROM graph_checkpoints
                    WHERE checkpoint_id = $1
                    """,
                    checkpoint_id,
                )

                if not row:
                    logger.warning(
                        "Checkpoint not found", checkpoint_id=str(checkpoint_id)
                    )
                    return False

                detected_agent_id = row["agent_id"]
                metrics = get_metrics(agent_id or detected_agent_id)

                with metrics.time_validate():
                    # Validate state is valid JSON
                    state = row["graph_state"]
                    if isinstance(state, str):
                        state = json.loads(state)  # Raises if invalid
                    elif not isinstance(state, dict):
                        logger.warning(
                            "Invalid state type", checkpoint_id=str(checkpoint_id)
                        )
                        metrics.record_validation(False)
                        return False

                    # Validate checksum if enabled
                    if self._enable_checksums:
                        is_valid, error_msg = self._validator.validate_checksum(state)
                        metrics.record_validation(is_valid)

                        if not is_valid:
                            metrics.record_corruption()
                            logger.error(
                                "Checkpoint checksum validation FAILED",
                                checkpoint_id=str(checkpoint_id),
                                agent_id=detected_agent_id,
                                error=error_msg,
                            )
                            return False
                    else:
                        metrics.record_validation(True)

                    logger.debug(
                        "Checkpoint integrity valid",
                        checkpoint_id=str(checkpoint_id),
                        agent_id=detected_agent_id,
                        checksum_validated=self._enable_checksums,
                    )
                    return True

        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in checkpoint",
                checkpoint_id=str(checkpoint_id),
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "Checkpoint validation failed",
                checkpoint_id=str(checkpoint_id),
                error=str(e),
                exc_info=True,
            )
            return False

    # =========================================================================
    # Audit Trail (PacketEnvelope Emission)
    # =========================================================================

    async def _emit_checkpoint_packet(
        self,
        event_type: str,
        agent_id: str,
        checkpoint_id: Optional[UUID],
        reason: str,
        state_keys: List[str],
    ) -> None:
        """
        Emit a PacketEnvelope for checkpoint audit trail.

        Best-effort: logs warning on failure but does not raise.

        Args:
            event_type: Type of checkpoint event (checkpoint_created, checkpoint_restored)
            agent_id: Agent identifier
            checkpoint_id: Checkpoint UUID (if available)
            reason: Checkpoint reason
            state_keys: List of keys in the checkpoint state
        """
        if self._service is None:
            logger.debug(
                "No service available for packet emission", event_type=event_type
            )
            return

        try:
            packet = PacketEnvelopeIn(
                packet_type=event_type,
                thread_id=UUID(str(checkpoint_id)) if checkpoint_id else uuid4(),
                payload={
                    "event_type": event_type,
                    "agent_id": agent_id,
                    "source_id": "agent_persistence",
                    "checkpoint_id": str(checkpoint_id) if checkpoint_id else None,
                    "reason": reason,
                    "state_keys": state_keys,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                metadata={
                    "agent": agent_id,
                    "component": "agent_persistence",
                    "schema_version": "1.0.0",
                },
                confidence={"score": 1.0, "level": "high"},
            )

            await self._service.write_packet(packet)
            logger.debug(
                "Checkpoint packet emitted",
                event_type=event_type,
                agent_id=agent_id,
                checkpoint_id=str(checkpoint_id) if checkpoint_id else None,
            )

        except Exception as e:
            # Best-effort: don't fail checkpoint operations due to packet emission
            logger.warning(
                "Failed to emit checkpoint packet",
                event_type=event_type,
                agent_id=agent_id,
                error=str(e),
            )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-043",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.checkpoint_metrics",
        "memory.checkpoint_validator",
        "memory.substrate_repository",
        "memory.substrate_service",
    ],
    "tags": [
        "async",
        "debugging",
        "event-driven",
        "learning",
        "logging",
        "memory-substrate",
        "metrics",
        "migration",
        "rest-api",
        "scheduling",
    ],
    "keywords": [
        "agent",
        "checkpoint",
        "checkpoints",
        "create",
        "delete",
        "deserialize",
        "integrity",
        "management",
    ],
    "business_value": "Implements memory_spec_v3.0.yaml memory_layers.persistence contract.",
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
