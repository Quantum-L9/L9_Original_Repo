"""QueryRewriter — LLM-powered query rewrite + expansion for memory retrieval.

Uses gpt-4.1-mini (locked model) with deterministic fallback when LLM fails.
ADR compliance: structlog-only, timezone-aware, builtin generics, explicit zip.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "QueryRewriter",
    "module_version": "1.0.0",
    "status": "active",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RewriteResult:
    """Output of a query rewrite operation."""

    rewritten_query: str
    expansions: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    used_llm: bool = False


# ---------------------------------------------------------------------------
# LLM client protocol
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    """Protocol for LLM completion calls."""

    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str: ...


# ---------------------------------------------------------------------------
# System prompt (locked, deterministic)
# ---------------------------------------------------------------------------

_REWRITE_SYSTEM_PROMPT = (
    "You are a memory-retrieval query optimizer. Given a user query, produce:\n"
    "1. A rewritten query that is more precise for semantic search.\n"
    "2. Up to 3 expansion queries that cover related angles.\n"
    "Respond in this exact format:\n"
    "REWRITTEN: <rewritten query>\n"
    "EXPANSION: <expansion 1>\n"
    "EXPANSION: <expansion 2>\n"
    "EXPANSION: <expansion 3>\n"
    "Do NOT add any other text."
)


# ---------------------------------------------------------------------------
# QueryRewriter
# ---------------------------------------------------------------------------


class QueryRewriter:
    """Rewrites and expands queries via LLM with deterministic fallback.

    Fail-safe: if LLM call fails or times out, returns the original query
    with empty expansions. Never raises on LLM failure.
    """

    def __init__(self, *, llm_client: LLMClient) -> None:
        self._llm = llm_client
        logger.info("query_rewriter_initialized")

    async def rewrite(
        self,
        query: str,
        *,
        model: str = "gpt-4.1-mini",
        max_tokens: int = 256,
        timeout_s: float = 5.0,
    ) -> RewriteResult:
        """Rewrite and expand a query. Falls back to original on any failure."""
        if not query or not query.strip():
            return RewriteResult(rewritten_query=query)

        prompt = f"{_REWRITE_SYSTEM_PROMPT}\n\nQuery: {query}"

        try:
            raw = await asyncio.wait_for(
                self._llm.complete(
                    prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.1,
                ),
                timeout=timeout_s,
            )
            return self._parse_response(raw, original=query)
        except TimeoutError:
            logger.warning(
                "query_rewrite_timeout",
                query=query,
                timeout_s=timeout_s,
            )
            return RewriteResult(rewritten_query=query)
        except Exception:
            logger.warning("query_rewrite_llm_error", exc_info=True, query=query)
            return RewriteResult(rewritten_query=query)

    @staticmethod
    def _parse_response(raw: str, *, original: str) -> RewriteResult:
        """Parse structured LLM output into RewriteResult."""
        rewritten = original
        expansions: list[str] = []

        for line in raw.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("REWRITTEN:"):
                candidate = line.split(":", 1)[1].strip()
                if candidate:
                    rewritten = candidate
            elif line.upper().startswith("EXPANSION:"):
                candidate = line.split(":", 1)[1].strip()
                if candidate:
                    expansions.append(candidate)

        return RewriteResult(
            rewritten_query=rewritten,
            expansions=expansions[:3],
            used_llm=True,
        )


__all__ = [
    "LLMClient",
    "QueryRewriter",
    "RewriteResult",
]

__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
