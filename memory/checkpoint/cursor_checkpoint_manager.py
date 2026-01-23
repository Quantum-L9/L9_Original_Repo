"""
L9 Cursor Checkpoint Manager
Version: 1.0.0

Dual checkpoint strategy: PostgresSaver (primary) + PacketEnvelope (fallback).
Implements Decision 3 + Decision 6 from design clarifications.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cursor Checkpoint Manager",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "cursor_checkpoint_manager",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "agents.cursor.integrations.cursor_executor",
            "api.server",
            "memory.checkpoint.__init__",
            "tests.integration.test_cursor_langgraph_integration",
        ],
    },
}
# ============================================================================

from typing import Any, Dict, Optional

import structlog

from agents.cursor.integrations.cursor_gateway import CursorMemoryGateway
from agents.cursor.integrations.cursor_langgraph import CursorAgentState
from memory.checkpoint.postgres_saver import L9PostgresSaver

logger = structlog.get_logger(__name__)


class CursorCheckpointManager:
    """
    Dual checkpoint manager per Decision 3 + Decision 6.

    Priority (Decision 6):
    1. PostgresSaver (LangGraph-native)
    2. PacketEnvelope (L9 substrate fallback)
    """

    def __init__(
        self,
        postgres_saver: L9PostgresSaver,
        memory_gateway: CursorMemoryGateway,
    ):
        """
        Initialize checkpoint manager.

        Args:
            postgres_saver: L9PostgresSaver for LangGraph-native checkpoints
            memory_gateway: CursorMemoryGateway for PacketEnvelope checkpoints
        """
        self._postgres_saver = postgres_saver
        self._memory_gateway = memory_gateway
        logger.info("CursorCheckpointManager initialized")

    async def checkpoint(
        self,
        thread_id: str,
        state: CursorAgentState,
    ) -> Dict[str, Any]:
        """
        Save dual checkpoint per Decision 3.

        Args:
            thread_id: Thread identifier
            state: CursorAgentState to checkpoint

        Returns:
            Dict with checkpoint_id, packet_id, source
        """
        logger.info("Saving dual checkpoint", thread_id=thread_id)

        # 1. Save to PostgresSaver (LangGraph-native)
        config = {"configurable": {"thread_id": thread_id}}

        # Convert state to checkpoint format
        checkpoint_data = state.model_dump() if hasattr(state, "model_dump") else state
        metadata = {}
        new_versions = {}

        try:
            checkpoint_result = await self._postgres_saver.put(
                config=config,
                checkpoint=checkpoint_data,
                metadata=metadata,
                new_versions=new_versions,
            )
            checkpoint_id = checkpoint_result.get("checkpoint_id")
        except Exception as e:
            logger.error("Failed to save PostgresSaver checkpoint", error=str(e))
            checkpoint_id = None

        # 2. Save to PacketEnvelope (L9 substrate)
        try:
            packet_id = await self._memory_gateway.write_checkpoint(
                thread_id=thread_id,
                state=state,
            )
        except Exception as e:
            logger.error("Failed to save PacketEnvelope checkpoint", error=str(e))
            packet_id = None

        logger.info(
            "Dual checkpoint saved",
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            packet_id=str(packet_id) if packet_id else None,
        )

        return {
            "checkpoint_id": checkpoint_id,
            "packet_id": str(packet_id) if packet_id else None,
            "source": "dual",
        }

    async def restore(
        self,
        thread_id: str,
    ) -> Optional[CursorAgentState]:
        """
        Restore checkpoint per Decision 6 priority.

        Priority:
        1. PostgresSaver (if present)
        2. PacketEnvelope (fallback)

        Args:
            thread_id: Thread identifier

        Returns:
            CursorAgentState if found, None otherwise
        """
        logger.info("Restoring checkpoint", thread_id=thread_id)

        # Try PostgresSaver first
        config = {"configurable": {"thread_id": thread_id}}
        try:
            checkpoint = await self._postgres_saver.get(config)

            if checkpoint:
                logger.info("Restored from PostgresSaver", thread_id=thread_id)
                # Convert Checkpoint to CursorAgentState
                if isinstance(checkpoint, dict):
                    return CursorAgentState(**checkpoint)
                elif hasattr(checkpoint, "model_dump"):
                    return CursorAgentState(**checkpoint.model_dump())
                else:
                    # Try to extract state from checkpoint
                    if isinstance(checkpoint, CursorAgentState):
                        return checkpoint
        except Exception as e:
            logger.warning("Failed to restore from PostgresSaver", error=str(e))

        # Fallback to PacketEnvelope
        try:
            state = await self._memory_gateway.load_checkpoint(thread_id)

            if state:
                logger.info("Restored from PacketEnvelope", thread_id=thread_id)
                return state
        except Exception as e:
            logger.warning("Failed to restore from PacketEnvelope", error=str(e))

        logger.warning("No checkpoint found", thread_id=thread_id)
        return None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-053",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.cursor.integrations.cursor_gateway",
        "agents.cursor.integrations.cursor_langgraph",
        "memory.checkpoint.postgres_saver",
    ],
    "tags": ["async", "learning", "logging", "memory-substrate", "rest-api", "service"],
    "keywords": ["checkpoint", "cursor", "decision", "manager", "restore"],
    "business_value": "Implements Decision 3 + Decision 6 from design clarifications.",
    "last_modified": "2026-01-14T15:03:00Z",
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
