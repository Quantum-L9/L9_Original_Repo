"""
Context window assembly strategies.

Implements 6 strategies for managing LLM context: naive, recency, summary, RAG, hybrid, adaptive.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Context Strategies",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "context_strategies",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["tests.core.observability.test_observability_integration"],
    },
}
# ============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class ContextStrategy(ABC):
    """Base class for context window strategies."""

    @abstractmethod
    @must_stay_async("callers use await")
    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context for LLM input."""
        pass


class NaiveTruncationStrategy(ContextStrategy):
    """Keep recent messages until budget exhausted (simple, lossy)."""

    @must_stay_async("callers use await")
    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context by naive truncation."""
        result = []
        token_count = 0

        for msg in reversed(conversation):
            msg_tokens = len(msg.get("content", "").split())
            if token_count + msg_tokens > max_tokens:
                logger.debug(
                    f"Truncation: dropping message, would exceed {max_tokens} tokens"
                )
                break
            result.append(f"{msg['role']}: {msg['content']}")
            token_count += msg_tokens

        return "\n".join(reversed(result))


class RecencyBiasedWindowStrategy(ContextStrategy):
    """Prioritize recent messages with some historical anchors (recommended default)."""

    def __init__(self, recent_percent: float = 0.7):
        """Initialize strategy.

        Args:
            recent_percent: Fraction (0-1) of budget reserved for recent messages.
        """
        self.recent_percent = recent_percent

    @must_stay_async("callers use await")
    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context with recency bias."""
        if not conversation:
            return ""

        recent_budget = int(max_tokens * self.recent_percent)
        anchor_budget = max_tokens - recent_budget
        result = []
        recent_token_count = 0
        anchor_token_count = 0

        # Recent messages (most important) - use recent_budget
        recent_count = 0
        for msg in reversed(conversation):
            msg_tokens = len(msg.get("content", "").split())
            if recent_token_count + msg_tokens > recent_budget:
                break
            result.append(f"{msg['role']}: {msg['content']}")
            recent_token_count += msg_tokens
            recent_count += 1

        # Anchor messages (system prompts, initial context) - use anchor_budget
        anchor_count = 0
        for msg in conversation:
            if anchor_count >= 2:  # Keep just first 2 as anchors
                break
            msg_tokens = len(msg.get("content", "").split())
            if anchor_token_count + msg_tokens > anchor_budget:
                break
            result.insert(0, f"{msg['role']}: {msg['content']}")
            anchor_token_count += msg_tokens
            anchor_count += 1

        total_tokens = recent_token_count + anchor_token_count
        logger.debug(
            f"RecencyWindow: {recent_count} recent ({recent_token_count} tokens), "
            f"{anchor_count} anchors ({anchor_token_count} tokens), "
            f"total={total_tokens}/{max_tokens}"
        )
        return "\n".join(result)


class HierarchicalSummarizationStrategy(ContextStrategy):
    """Summarize older context, keep recent turns full (good for long threads)."""

    def __init__(self, summary_ratio: float = 0.25):
        """Initialize strategy.

        Args:
            summary_ratio: Fraction of budget to use for summaries.
        """
        self.summary_ratio = summary_ratio

    @must_stay_async("callers use await")
    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context with summarization of history."""
        if not conversation:
            return ""

        summary_budget = int(max_tokens * self.summary_ratio)
        recent_budget = max_tokens - summary_budget

        # Keep recent messages full
        result = []
        token_count = 0
        recent_start = len(conversation)

        for msg in reversed(conversation):
            msg_tokens = len(msg.get("content", "").split())
            if token_count + msg_tokens > recent_budget:
                break
            result.append(f"{msg['role']}: {msg['content']}")
            token_count += msg_tokens
            recent_start -= 1

        # Summarize older messages (stub: in production, use LLM to summarize)
        if recent_start > 0:
            older = conversation[:recent_start]
            summary = f"[Summary of {len(older)} earlier messages]\n"
            for msg in older[:3]:  # Just list first few as placeholders
                summary += f"- {msg['role']}: {msg['content'][:50]}...\n"
            result.insert(0, summary)
            token_count += len(summary.split())

        logger.debug(
            f"HierarchicalSummary: {len(older)} older msgs summarized, {token_count} total tokens"
        )
        return "\n".join(result)


class RAGStrategy(ContextStrategy):
    """Retrieve relevant chunks from knowledge base (good for knowledge queries)."""

    def __init__(self, top_k: int = 5, min_relevance: float = 0.5):
        """Initialize RAG strategy.

        Args:
            top_k: Number of chunks to retrieve.
            min_relevance: Minimum relevance score (0-1).
        """
        self.top_k = top_k
        self.min_relevance = min_relevance

    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context with RAG retrieval."""
        if not conversation or not knowledge_base:
            return ""

        # Get most recent user query
        query = next(
            (msg["content"] for msg in reversed(conversation) if msg["role"] == "user"),
            None,
        )
        if not query:
            return ""

        # Retrieve relevant chunks (stub: in production, use vector DB)
        retrieved = (
            await knowledge_base.retrieve(
                query=query,
                top_k=self.top_k,
                min_relevance=self.min_relevance,
            )
            if hasattr(knowledge_base, "retrieve")
            else []
        )

        result = []
        if retrieved:
            result.append("[Knowledge Base Results]")
            for chunk in retrieved:
                result.append(f"- {chunk.get('content', chunk)[:200]}")

        # Append recent conversation
        recent_msgs = [f"{msg['role']}: {msg['content']}" for msg in conversation[-3:]]
        result.extend(recent_msgs)

        token_count = len(" ".join(result).split())
        logger.debug(f"RAG: retrieved {len(retrieved)} chunks, {token_count} tokens")
        return "\n".join(result)


class HybridStrategy(ContextStrategy):
    """Combine RAG + summarization + recency (best quality, highest cost)."""

    def __init__(
        self,
        rag_percent: float = 0.5,
        summary_percent: float = 0.3,
        recent_percent: float = 0.2,
    ):
        """Initialize hybrid strategy."""
        self.rag_percent = rag_percent
        self.summary_percent = summary_percent
        self.recent_percent = recent_percent

    async def assemble(
        self,
        conversation: List[Dict[str, str]],
        knowledge_base: Optional[Any] = None,
        max_tokens: int = 8000,
    ) -> str:
        """Assemble context using all three strategies."""
        result = []

        # 50% for RAG
        if knowledge_base:
            rag_strategy = RAGStrategy(top_k=5)
            rag_context = await rag_strategy.assemble(
                conversation,
                knowledge_base,
                int(max_tokens * self.rag_percent),
            )
            if rag_context:
                result.append(rag_context)

        # 30% for summarization
        summary_strategy = HierarchicalSummarizationStrategy()
        summary_context = await summary_strategy.assemble(
            conversation,
            None,
            int(max_tokens * self.summary_percent),
        )
        if summary_context:
            result.append(summary_context)

        # 20% for recent
        recency_strategy = RecencyBiasedWindowStrategy(recent_percent=1.0)
        recent_context = await recency_strategy.assemble(
            conversation,
            None,
            int(max_tokens * self.recent_percent),
        )
        if recent_context:
            result.append(recent_context)

        logger.debug(
            f"Hybrid: RAG + Summary + Recency combined, {len(' '.join(result).split())} tokens"
        )
        return "\n\n".join(result)


class AdaptiveStrategySelector:
    """Select optimal strategy based on task characteristics."""

    @must_stay_async("callers use await")
    async def select_strategy(
        self,
        conversation: List[Dict[str, str]],
        task_type: Optional[str] = None,
        knowledge_base_available: bool = False,
    ) -> ContextStrategy:
        """Select best strategy for this task."""
        if task_type == "knowledge_query" and knowledge_base_available:
            return HybridStrategy()
        elif task_type == "long_research":
            return HierarchicalSummarizationStrategy()
        elif knowledge_base_available:
            return HybridStrategy()
        else:
            return RecencyBiasedWindowStrategy()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-061",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "core",
        "debugging",
        "foundation",
        "logging",
        "messaging",
        "service",
    ],
    "keywords": [
        "adaptive",
        "assemble",
        "biased",
        "hierarchical",
        "hybrid",
        "naive",
        "recency",
        "select",
    ],
    "business_value": "Implements 6 strategies for managing LLM context: naive, recency, summary, RAG, hybrid, adaptive.",
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
