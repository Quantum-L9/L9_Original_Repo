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

import asyncio
import structlog
from datetime import datetime
from typing import Any, Optional, Dict, List

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
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a thread (LangGraph interface).

        Returns list of checkpoint metadata dicts sorted by creation time (newest first).

        Args:
            config: LangGraph config dict with configurable.thread_id
            filter: Optional filter criteria (not yet implemented)
            before: Optional checkpoint to list before (not yet implemented)
            limit: Maximum number of checkpoints to return (default 100)

        Returns:
            List of checkpoint metadata dicts
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.debug("list_checkpoints_no_thread_id")
            return []

        agent_id = f"cursor:{thread_id}"
        effective_limit = limit or 100

        try:
            # Query checkpoints via repository
            # Uses graph_checkpoints table with agent_id pattern matching
            checkpoints = await self._repository.list_checkpoints_by_agent(
                agent_id=agent_id,
                limit=effective_limit,
            )

            logger.debug(
                "list_checkpoints_success",
                thread_id=thread_id,
                count=len(checkpoints),
            )

            return checkpoints

        except AttributeError:
            # Repository doesn't have list_checkpoints_by_agent yet
            # Fallback: return empty list with warning
            logger.warning(
                "list_checkpoints_not_supported",
                thread_id=thread_id,
                reason="repository.list_checkpoints_by_agent not available",
            )
            return []
        except Exception as e:
            logger.error(
                "list_checkpoints_error",
                thread_id=thread_id,
                error=str(e),
            )
            return []


class L9RetryablePostgresSaver(L9PostgresSaver):
    """
    L9PostgresSaver with automatic retry + exponential backoff.

    Production-ready wrapper that adds:
    - Automatic retry with exponential backoff on transient failures
    - Connection pool health monitoring
    - Structured logging for observability

    Source: Perplexity research GMP-105, LangGraph best practices 2026
    """

    def __init__(
        self,
        repository: Optional[SubstrateRepository] = None,
        max_retries: int = 3,
        base_retry_delay: float = 0.1,
    ):
        """
        Initialize L9 Retryable PostgresSaver.

        Args:
            repository: SubstrateRepository instance (uses singleton if None)
            max_retries: Maximum retry attempts (default 3)
            base_retry_delay: Base delay in seconds for exponential backoff (default 0.1)
        """
        super().__init__(repository)
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        logger.info(
            "L9RetryablePostgresSaver initialized",
            max_retries=max_retries,
            base_retry_delay=base_retry_delay,
        )

    async def _execute_with_retry(
        self,
        operation_name: str,
        operation_func,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute checkpoint operation with exponential backoff retry.

        Args:
            operation_name: Name of operation for logging
            operation_func: Async function to execute
            *args: Positional arguments to pass
            **kwargs: Keyword arguments to pass

        Returns:
            Result of operation_func

        Raises:
            Last exception if all retries exhausted
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                result = await operation_func(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        "checkpoint_operation_recovered",
                        operation=operation_name,
                        attempt=attempt + 1,
                    )

                return result

            except Exception as e:
                last_exception = e
                delay = self.base_retry_delay * (2**attempt)

                logger.warning(
                    "checkpoint_operation_retry",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    delay_seconds=delay,
                    error=str(e),
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)

        logger.error(
            "checkpoint_operation_failed",
            operation=operation_name,
            error=str(last_exception),
        )
        raise last_exception  # type: ignore[misc]

    async def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Save checkpoint with retry logic and observability.

        Args:
            config: LangGraph config dict with configurable.thread_id
            checkpoint: LangGraph Checkpoint object
            metadata: Checkpoint metadata
            new_versions: New version information

        Returns:
            Dict with checkpoint_id
        """
        start_time = datetime.utcnow()

        result = await self._execute_with_retry(
            "put",
            super().put,
            config,
            checkpoint,
            metadata,
            new_versions,
        )

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            "checkpoint_saved_with_retry",
            thread_id=config.get("configurable", {}).get("thread_id"),
            checkpoint_id=result.get("checkpoint_id"),
            duration_ms=round(duration_ms, 2),
        )

        return result

    async def get(
        self,
        config: Dict[str, Any],
    ) -> Optional[Checkpoint]:
        """
        Load checkpoint with retry logic.

        Args:
            config: LangGraph config dict with configurable.thread_id

        Returns:
            Checkpoint object or None
        """
        return await self._execute_with_retry(
            "get",
            super().get,
            config,
        )

    async def list(
        self,
        config: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints with retry logic.

        Args:
            config: LangGraph config dict
            filter: Optional filter criteria
            before: Optional checkpoint to list before
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint metadata dicts
        """
        return await self._execute_with_retry(
            "list",
            super().list,
            config,
            filter=filter,
            before=before,
            limit=limit,
        )

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics for monitoring.

        Returns pool stats if repository has pool access, otherwise returns
        placeholder stats indicating pool monitoring is not available.

        Returns:
            Dict with pool_size, pool_available, requests_waiting, timestamp
        """
        stats = {
            "pool_size": -1,
            "pool_available": -1,
            "requests_waiting": -1,
            "monitoring_available": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Try to get pool stats from repository if available
        if hasattr(self._repository, "get_pool_stats"):
            try:
                repo_stats = self._repository.get_pool_stats()
                stats.update(repo_stats)
                stats["monitoring_available"] = True
            except Exception as e:
                logger.debug("pool_stats_unavailable", error=str(e))

        return stats


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
