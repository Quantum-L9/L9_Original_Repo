# agents/cursor/cursor_retrieval_kernel.py
"""
Enforces: Check working memory → long-term memory → repo (no skipping)
This is the core of eliminating grepping.

Async-compatible for L9 architecture.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memory_cache.cursor_working_memory_service import CursorWorkingMemoryService


class RetrievalSource(str, Enum):
    """
    Decision engine managing cursor context retrieval order, ensuring cache and memory checks precede repository scans for efficient knowledge access.

    Args:
        retrieval_source (RetrievalSource): The current source from which to retrieve cursor context.
        cache (dict): In-memory cache of retrieved data.
        memory (dict): Long-term memory storage for cursor contexts.
        repo (Repository): Repository interface for scanning external sources.

    Returns:
        str: The selected retrieval source based on current cache and memory state.

    Raises:
        ValueError: If an invalid retrieval source is provided.
    """

    WORKING_MEMORY = "working_memory"
    LONG_TERM_MEMORY = "long_term_memory"
    REPO_SCAN = "repo_scan"


class CursorRetrievalKernel:
    """
    Decision engine for Cursor context retrieval.

    Invariant: NEVER repo-scan before checking cache + memory.
    """

    def __init__(
        self,
        wmc: CursorWorkingMemoryService,
        memory_service,
        logger=None,
    ):
        """Initialize the retrieval kernel.

        Args:
            wmc: Working memory cache service.
            memory_service: Long-term memory service for semantic search.
            logger: Optional logging function.
        """
        self.wmc = wmc
        self.memory = memory_service
        self.logger = logger or self._noop_logger

    @staticmethod
    def _noop_logger(*args, **kwargs):
        """No-op logger for when no logger is provided."""
        pass

    async def retrieve_context(
        self,
        repo_id: str,
        branch: str,
        query: str,
        context_type: str | None = None,  # "file", "function", "pattern"
    ) -> tuple[RetrievalSource, dict[str, Any]]:
        """
        Three-tier retrieval: working memory → long-term → repo.

        Args:
            repo_id, branch: scope
            query: "where is X", "how do we handle Y", etc
            context_type: hint for ranking (optional)

        Returns:
            (source, data) tuple indicating where answer came from

        Invariant: NEVER returns (REPO_SCAN, None). If repo_scan needed,
                   data field contains instruction to scan (not results).
        """

        # TIER 1: Working Memory (same session)
        wmc_context = await self._check_working_memory(repo_id, branch, query)
        if wmc_context:
            self.logger(f"[CursorKernel] working memory HIT: {query}")
            return (RetrievalSource.WORKING_MEMORY, wmc_context)

        # TIER 2: Long-Term Memory (semantic + hybrid search)
        ltm_context = await self._check_long_term_memory(query, context_type)
        if ltm_context:
            self.logger(f"[CursorKernel] long-term memory HIT: {query}")
            return (RetrievalSource.LONG_TERM_MEMORY, ltm_context)

        # TIER 3: Repo Scan (controlled, logged)
        self.logger(f"[CursorKernel] falling back to repo scan: {query}")
        return (RetrievalSource.REPO_SCAN, {"instruction": "scan_repo", "query": query})

    async def _check_working_memory(
        self,
        repo_id: str,
        branch: str,
        query: str,
    ) -> dict[str, Any] | None:
        """
        Check WMC for relevant context.
        Fast, exact match only.
        """
        snapshot = await self.wmc.hydrate(repo_id, branch)
        if not snapshot:
            return None

        # Simple heuristics: does query match recent context?
        query_lower = query.lower()

        # Check files touched
        for f in snapshot.files_touched:
            if query_lower in f.lower():
                return {
                    "source": "working_memory",
                    "type": "file_context",
                    "files": snapshot.files_touched[-10:],
                    "recent_decisions": snapshot.recent_decisions[-3:],
                }

        # Check intent
        if snapshot.intent and query_lower in snapshot.intent.lower():
            return {
                "source": "working_memory",
                "type": "intent_context",
                "intent": snapshot.intent,
                "hypotheses": snapshot.open_hypotheses,
            }

        return None

    async def _check_long_term_memory(
        self,
        query: str,
        context_type: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Query long-term memory (semantic search).
        """
        try:
            results = await self.memory.search(
                query=query,
                top_k=3,
                kind=None,  # don't filter by kind; let search decide
            )
            if results:
                return {
                    "source": "long_term_memory",
                    "type": "semantic_match",
                    "results": results,
                }
        except Exception as e:
            self.logger(f"[CursorKernel] long-term memory search failed: {e}")

        return None

    def mark_repo_scan_necessary(
        self,
        query: str,
        reason: str = "no_cache_hit",
    ) -> None:
        """
        Log when repo scan is unavoidable (for metrics/audit).
        """
        self.logger(f"[CursorKernel] repo scan required: {reason} (query: {query})")
