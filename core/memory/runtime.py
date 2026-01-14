"""
L9 Memory Runtime - Kernel Evolution Logging
=============================================

Provides functions for logging kernel evolution events to the memory substrate.
This enables tracking of kernel changes over time for audit and learning.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
        kernel_ids: List[str],
        previous_hashes: Dict[str, str],
        new_hashes: Dict[str, str],
        modified_kernels: List[str],
        trigger: str,  # manual, auto, gmp, self_reflection
        success: bool,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_id = str(uuid4())
        self.timestamp = datetime.now(timezone.utc)
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

    def to_packet_payload(self) -> Dict[str, Any]:
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


async def log_kernel_evolution(
    event_type: str,
    agent_id: str,
    kernel_ids: List[str],
    previous_hashes: Dict[str, str],
    new_hashes: Dict[str, str],
    modified_kernels: List[str],
    trigger: str = "manual",
    success: bool = True,
    errors: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
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
        from core.schemas import PacketEnvelope, PacketKind

        packet = PacketEnvelope(
            source_id="kernel_loader",
            agent_id=agent_id,
            thread_id=f"kernel_evolution_{event.event_id}",
            kind=PacketKind.SYSTEM,
            payload=event.to_packet_payload(),
            metadata={
                "event_type": "KERNEL_EVOLUTION",
                "trigger": trigger,
                "success": success,
                "modified_count": len(modified_kernels),
            },
            confidence=1.0,  # System events have full confidence
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
        else:
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
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
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
    "log_kernel_evolution",
    "get_kernel_evolution_history",
]

