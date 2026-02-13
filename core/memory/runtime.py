"""
L9 Memory Runtime - Kernel Evolution Logging
=============================================

Provides functions for logging kernel evolution events to the memory substrate.
This enables tracking of kernel changes over time for audit and learning.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Kernel Evolution Logging",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "foundation",
    "domain": "memory_substrate",
    "module_name": "runtime",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server", "tests.integration.test_kernel_hot_reload"],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Kernel Evolution Logging
# =============================================================================


class KernelEvolutionEvent:
    """Represents a kernel evolution event for logging."""

    def __init__(
        self,
        event_type: str,  # RELOAD, MODIFY, EVOLVE, ROLLBACK
        agent_id: str,
        kernel_ids: list[str],
        previous_hashes: dict[str, str],
        new_hashes: dict[str, str],
        modified_kernels: list[str],
        trigger: str,  # manual, auto, gmp, self_reflection
        success: bool,
        errors: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Represents a kernel evolution event for logging kernel lifecycle changes in the memory substrate.

        Args:
            event_type: Type of event such as RELOAD, MODIFY, EVOLVE, or ROLLBACK.
            agent_id: Identifier of the agent performing the event.
            kernel_ids: List of kernel identifiers involved in the event.
            previous_hashes: Mapping of kernel IDs to their previous hashes.
            new_hashes: Mapping of kernel IDs to their new hashes.
            modified_kernels: List of kernels that were modified.
            trigger: Cause of the event, e.g., manual or auto.
            success: Boolean indicating if the event succeeded.
            errors: List of error messages if any occurred.
            metadata: Additional metadata related to the event.
        """
        self.event_id = str(uuid4())
        self.timestamp = datetime.now(UTC)
        self.event_type = event_type
        self.agent_id = agent_id
        self.kernel_ids = kernel_ids
        self.previous_hashes = previous_hashes
        self.new_hashes = new_hashes
        self.modified_kernels = modified_kernels
        self.trigger = trigger
        self.success = success
        self.errors = errors or []
        self.metadata = metadata or {}

    def to_packet_payload(self) -> dict[str, Any]:
        """Convert to PacketEnvelope payload format."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "kernel_ids": self.kernel_ids,
            "modified_kernels": self.modified_kernels,
            "trigger": self.trigger,
            "success": self.success,
            "errors": self.errors,
            "hash_changes": {
                kernel_id: {
                    "previous": self.previous_hashes.get(kernel_id, ""),
                    "new": self.new_hashes.get(kernel_id, ""),
                }
                for kernel_id in self.modified_kernels
            },
            "metadata": self.metadata,
        }


@must_stay_async("callers use await")
async def log_kernel_evolution(
    event_type: str,
    agent_id: str,
    kernel_ids: list[str],
    previous_hashes: dict[str, str],
    new_hashes: dict[str, str],
    modified_kernels: list[str],
    trigger: str = "manual",
    success: bool = True,
    errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Log a kernel evolution event to the memory substrate.

    This function records kernel changes (reload, modify, evolve, rollback)
    to the PostgreSQL packet store for audit and learning purposes.

    Args:
        event_type: Type of evolution event (RELOAD, MODIFY, EVOLVE, ROLLBACK)
        agent_id: ID of the agent whose kernels evolved
        kernel_ids: List of all kernel IDs involved
        previous_hashes: Hash snapshot before evolution
        new_hashes: Hash snapshot after evolution
        modified_kernels: List of kernel IDs that were modified
        trigger: What triggered the evolution (manual, auto, gmp, self_reflection)
        success: Whether the evolution succeeded
        errors: List of error messages if any
        metadata: Additional metadata to include

    Returns:
        The event_id if successfully logged, None otherwise
    """
    event = KernelEvolutionEvent(
        event_type=event_type,
        agent_id=agent_id,
        kernel_ids=kernel_ids,
        previous_hashes=previous_hashes,
        new_hashes=new_hashes,
        modified_kernels=modified_kernels,
        trigger=trigger,
        success=success,
        errors=errors,
        metadata=metadata,
    )

    logger.info(
        "kernel_evolution.logging",
        event_id=event.event_id,
        event_type=event_type,
        agent_id=agent_id,
        modified_count=len(modified_kernels),
        success=success,
    )

    try:
        # Try to import and use the memory substrate service
        from memory.substrate_service import get_service

        substrate = await get_service()
        if substrate is None:
            logger.warning(
                "kernel_evolution.substrate_unavailable",
                event_id=event.event_id,
            )
            return event.event_id  # Return ID even if not persisted

        # Build packet envelope
        from core.schemas import PacketEnvelope

        packet = PacketEnvelope(
            packet_type="system",
            payload=event.to_packet_payload(),
            provenance={"source": "kernel_loader"},
            metadata={
                "agent": agent_id,
                "event_type": "KERNEL_EVOLUTION",
                "trigger": trigger,
                "success": success,
                "modified_count": len(modified_kernels),
                "thread_id": f"kernel_evolution_{event.event_id}",
            },
            confidence={"score": 1.0},  # System events have full confidence
        )

        # Ingest packet
        result = await substrate.ingest_packet(packet)
        if result and result.success:
            logger.info(
                "kernel_evolution.logged",
                event_id=event.event_id,
                packet_id=result.packet_id,
            )
            return event.event_id
        logger.warning(
            "kernel_evolution.ingest_failed",
            event_id=event.event_id,
            error=result.error if result else "unknown",
        )
        return event.event_id

    except ImportError as e:
        logger.debug(
            "kernel_evolution.substrate_not_available",
            event_id=event.event_id,
            error=str(e),
        )
        return event.event_id

    except Exception as e:
        logger.error(
            "kernel_evolution.logging_failed",
            event_id=event.event_id,
            error=str(e),
            exc_info=True,
        )
        return event.event_id


async def get_kernel_evolution_history(
    agent_id: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve kernel evolution history from the memory substrate.

    Args:
        agent_id: Filter by agent ID (optional)
        event_type: Filter by event type (optional)
        limit: Maximum number of events to return

    Returns:
        List of kernel evolution events
    """
    try:
        from memory.substrate_service import get_service

        substrate = await get_service()
        if substrate is None:
            logger.warning("kernel_evolution.history_substrate_unavailable")
            return []

        # Build filter
        filters = {"metadata.event_type": "KERNEL_EVOLUTION"}
        if agent_id:
            filters["agent_id"] = agent_id
        if event_type:
            filters["payload.event_type"] = event_type

        # Query packets
        packets = await substrate.search_packets(
            filters=filters,
            limit=limit,
            order_by="created_at",
            order_desc=True,
        )

        return [p.get("payload", {}) for p in packets]

    except ImportError:
        logger.debug("kernel_evolution.history_substrate_not_available")
        return []

    except Exception as e:
        logger.error(
            "kernel_evolution.history_failed",
            error=str(e),
            exc_info=True,
        )
        return []


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "KernelEvolutionEvent",
    "get_kernel_evolution_history",
    "log_kernel_evolution",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-023",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "audit-tool",
        "debugging",
        "event-driven",
        "foundation",
        "logging",
        "memory-substrate",
        "messaging",
        "security",
    ],
    "keywords": [
        "audit",
        "event",
        "evolution",
        "history",
        "kernel",
        "log",
        "logging",
        "memory",
    ],
    "business_value": "Provides functions for logging kernel evolution events to the memory substrate.",
    "last_modified": "2026-01-14T13:21:36Z",
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
