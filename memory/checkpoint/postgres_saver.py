"""
L9 LangGraph PostgresSaver
Version: 1.0.0

Wraps L9 checkpoint infrastructure to implement LangGraph BaseCheckpointSaver interface.
Uses existing graph_checkpoints table via SubstrateRepository.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Postgres Saver",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "postgres_saver",
    "type": "service",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.server",
            "memory.checkpoint.__init__",
            "memory.checkpoint.cursor_checkpoint_manager",
            "tests.integration.test_cursor_langgraph_integration",
        ],
    },
}
# ============================================================================

import structlog
from typing import Any, Optional, Dict

# LangGraph checkpoint interface (if available)
try:
    from langgraph.checkpoint.base import (
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointMetadata,
    )

    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback: define minimal interface
    LANGGRAPH_AVAILABLE = False
    BaseCheckpointSaver = object
    Checkpoint = Dict[str, Any]
    CheckpointMetadata = Dict[str, Any]

from memory.substrate_repository import SubstrateRepository, get_repository
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class L9PostgresSaver(BaseCheckpointSaver):
    """
    LangGraph-compatible checkpoint saver using L9's graph_checkpoints table.

    Implements BaseCheckpointSaver interface for LangGraph integration.
    Uses existing SubstrateRepository.save_checkpoint() / get_checkpoint().
    """

    def __init__(self, repository: Optional[SubstrateRepository] = None):
        """
        Initialize L9 PostgresSaver.

        Args:
            repository: SubstrateRepository instance (uses singleton if None)
        """
        self._repository = repository or get_repository()
        logger.info("L9PostgresSaver initialized")

    @property
    def repository(self) -> SubstrateRepository:
        """Get repository instance."""
        return self._repository

    async def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Save checkpoint (LangGraph interface).

        Maps LangGraph thread_id to L9 agent_id format: "cursor:{thread_id}"

        Args:
            config: LangGraph config dict with configurable.thread_id
            checkpoint: LangGraph Checkpoint object
            metadata: Checkpoint metadata
            new_versions: New version information

        Returns:
            Dict with checkpoint_id
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id required in config.configurable")

        # Map to L9 agent_id format
        agent_id = f"cursor:{thread_id}"

        # Convert checkpoint to graph_state dict
        graph_state = {
            "checkpoint": checkpoint
            if isinstance(checkpoint, dict)
            else checkpoint.model_dump()
            if hasattr(checkpoint, "model_dump")
            else str(checkpoint),
            "metadata": metadata
            if isinstance(metadata, dict)
            else metadata.model_dump()
            if hasattr(metadata, "model_dump")
            else str(metadata),
            "new_versions": new_versions,
        }

        # Save via L9 repository
        checkpoint_id = await self._repository.save_checkpoint(
            agent_id=agent_id,
            graph_state=graph_state,
        )

        logger.debug(
            "Saved LangGraph checkpoint",
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
        )

        return {"checkpoint_id": str(checkpoint_id)}

    async def get(
        self,
        config: Dict[str, Any],
    ) -> Optional[Checkpoint]:
        """
        Load checkpoint (LangGraph interface).

        Returns Checkpoint if found, None otherwise.

        Args:
            config: LangGraph config dict with configurable.thread_id

        Returns:
            Checkpoint object or None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        agent_id = f"cursor:{thread_id}"

        # Load from L9 repository
        checkpoint_row = await self._repository.get_checkpoint(agent_id=agent_id)

        if not checkpoint_row:
            return None

        # Extract checkpoint from graph_state
        graph_state = checkpoint_row.graph_state
        checkpoint = graph_state.get("checkpoint")

        logger.debug(
            "Loaded LangGraph checkpoint",
            thread_id=thread_id,
            found=checkpoint is not None,
        )

        return checkpoint

    @must_stay_async("callers use await")
    async def list(
        self,
        config: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
    ) -> list[Dict[str, Any]]:
        """
        List checkpoints (LangGraph interface).

        Returns list of checkpoint metadata dicts.

        Args:
            config: LangGraph config dict
            filter: Optional filter criteria

        Returns:
            List of checkpoint metadata dicts
        """
        # For now, return empty list (can extend if needed)
        # L9's graph_checkpoints table uses agent_id as key, not thread_id
        # Would need additional query to list all cursor:* checkpoints
        logger.debug("List checkpoints called (not yet implemented)")
        return []


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-052",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "memory.substrate_repository"],
    "tags": [
        "async",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "service",
    ],
    "keywords": ["langgraph", "postgres", "repository", "saver"],
    "business_value": "Implements L9PostgresSaver for postgres saver functionality",
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
