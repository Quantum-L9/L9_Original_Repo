"""
L9 Memory - Hierarchical Summarizer
Version: 1.0.0

Implements tiered memory summarization with 20min → daily → weekly cascade.
Part of Stage 2: Hierarchical Memory Consolidation Engine (SUPER-PROMPT).

Architecture:
- 20-minute summaries: Capture session highlights
- Daily summaries: Compress 20-min summaries into daily digests
- Weekly summaries: Roll up daily summaries into weekly overviews

Each tier has configurable compression ratios and LLM prompts.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Hierarchical Summarizer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "hierarchical_summarizer",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "memory.__init__",
            "tests.memory.test_hierarchical_consolidation",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class SummaryTier(str, Enum):
    """Memory summarization tiers with increasing time horizons."""

    SESSION = "session"  # 20-minute summaries
    DAILY = "daily"  # Daily rollups
    WEEKLY = "weekly"  # Weekly digests
    PERMANENT = "permanent"  # Promoted to identity tier


@dataclass
class SummaryConfig:
    """Configuration for a summary tier."""

    tier: SummaryTier
    time_window_minutes: int
    max_source_items: int
    target_compression_ratio: float  # 0.15-0.25 typical
    min_importance_threshold: float
    prompt_template: str


@dataclass
class SummaryResult:
    """Result of a summarization operation."""

    summary_id: UUID = field(default_factory=uuid4)
    tier: SummaryTier = SummaryTier.SESSION
    source_count: int = 0
    summary_text: str = ""
    compression_ratio: float = 0.0
    importance_score: float = 0.5
    source_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


# Default tier configurations
DEFAULT_TIER_CONFIGS: dict[SummaryTier, SummaryConfig] = {
    SummaryTier.SESSION: SummaryConfig(
        tier=SummaryTier.SESSION,
        time_window_minutes=20,
        max_source_items=50,
        target_compression_ratio=0.25,
        min_importance_threshold=0.3,
        prompt_template="""Summarize the following session activity into a concise digest:

{content}

Requirements:
- Capture key decisions and outcomes
- Preserve important facts and entities
- Maintain chronological flow
- Target length: ~25% of original""",
    ),
    SummaryTier.DAILY: SummaryConfig(
        tier=SummaryTier.DAILY,
        time_window_minutes=1440,  # 24 hours
        max_source_items=100,
        target_compression_ratio=0.20,
        min_importance_threshold=0.4,
        prompt_template="""Create a daily summary from these session summaries:

{content}

Requirements:
- Synthesize themes across sessions
- Highlight key accomplishments
- Note important decisions and their rationale
- Target length: ~20% of combined input""",
    ),
    SummaryTier.WEEKLY: SummaryConfig(
        tier=SummaryTier.WEEKLY,
        time_window_minutes=10080,  # 7 days
        max_source_items=200,
        target_compression_ratio=0.15,
        min_importance_threshold=0.5,
        prompt_template="""Create a weekly overview from these daily summaries:

{content}

Requirements:
- Identify major themes and patterns
- Capture significant milestones
- Preserve critical decisions
- Note emerging trends
- Target length: ~15% of combined input""",
    ),
}


class HierarchicalSummarizer:
    """
    Hierarchical memory summarizer implementing tiered consolidation.

    Cascade: 20min → daily → weekly with configurable compression.
    Uses LLM for semantic summarization, preserves importance scoring.
    """

    def __init__(
        self,
        repository: Any | None = None,
        llm_client: Any | None = None,
        tier_configs: dict[SummaryTier, SummaryConfig] | None = None,
        dry_run: bool = False,
    ):
        """
        Initialize hierarchical summarizer.

        Args:
            repository: SubstrateRepository for DB access
            llm_client: Anthropic or OpenAI client for summarization
            tier_configs: Custom tier configurations (uses defaults if None)
            dry_run: If True, log operations without executing
        """
        self._repository = repository
        self._llm_client = llm_client
        self._tier_configs = tier_configs or DEFAULT_TIER_CONFIGS
        self._dry_run = dry_run

        logger.info(
            "HierarchicalSummarizer initialized",
            dry_run=dry_run,
            tiers=list(self._tier_configs.keys()),
        )

    @must_stay_async("callers use await")
    async def run_cascade(
        self,
        cutoff_time: datetime | None = None,
    ) -> dict[SummaryTier, list[SummaryResult]]:
        """
        Run full summarization cascade: session → daily → weekly.

        Args:
            cutoff_time: Process items before this time (default: now)

        Returns:
            Dict mapping tiers to generated summaries
        """
        cutoff_time = cutoff_time or datetime.now(UTC)
        results: dict[SummaryTier, list[SummaryResult]] = {}

        logger.info(
            "Starting hierarchical summarization cascade",
            cutoff=cutoff_time.isoformat(),
        )

        # Session tier: 20-minute windows
        results[SummaryTier.SESSION] = await self._summarize_tier(
            SummaryTier.SESSION,
            cutoff_time,
        )

        # Daily tier: Roll up session summaries
        results[SummaryTier.DAILY] = await self._summarize_tier(
            SummaryTier.DAILY,
            cutoff_time,
        )

        # Weekly tier: Roll up daily summaries
        results[SummaryTier.WEEKLY] = await self._summarize_tier(
            SummaryTier.WEEKLY,
            cutoff_time,
        )

        total_summaries = sum(len(v) for v in results.values())
        logger.info(
            "Hierarchical cascade complete",
            total_summaries=total_summaries,
            by_tier={k.value: len(v) for k, v in results.items()},
        )

        return results

    @must_stay_async("callers use await")
    async def _summarize_tier(
        self,
        tier: SummaryTier,
        cutoff_time: datetime,
    ) -> list[SummaryResult]:
        """
        Summarize items in a specific tier.

        Args:
            tier: Target summary tier
            cutoff_time: Process items before this time

        Returns:
            List of generated summaries
        """
        config = self._tier_configs[tier]
        results: list[SummaryResult] = []

        logger.debug(
            f"Processing {tier.value} tier", window_minutes=config.time_window_minutes
        )

        if self._dry_run:
            logger.info(f"DRY RUN: Would summarize {tier.value} tier")
            return results

        if self._repository is None:
            logger.warning("No repository configured, skipping summarization")
            return results

        # Get unsummarized items for this tier
        items = await self._get_unsummarized_items(tier, cutoff_time, config)

        if not items:
            logger.debug(f"No items to summarize for {tier.value}")
            return results

        # Group items by time window
        windows = self._group_by_time_window(items, config.time_window_minutes)

        for _window_start, window_items in windows.items():
            if len(window_items) < 2:
                continue  # Skip windows with too few items

            summary = await self._generate_summary(tier, window_items, config)
            if summary:
                results.append(summary)

                # Store summary in semantic_facts
                await self._store_summary(summary)

        logger.info(
            f"Tier {tier.value} summarization complete",
            summaries_generated=len(results),
            items_processed=len(items),
        )

        return results

    async def _get_unsummarized_items(
        self,
        tier: SummaryTier,
        cutoff_time: datetime,
        config: SummaryConfig,
    ) -> list[dict[str, Any]]:
        """Get items that haven't been summarized yet."""
        if self._repository is None:
            return []

        window_start = cutoff_time - timedelta(minutes=config.time_window_minutes)

        try:
            async with self._repository.acquire() as conn:
                # Query depends on tier
                if tier == SummaryTier.SESSION:
                    # Get raw packets
                    rows = await conn.fetch(
                        """
                        SELECT packet_id, envelope, created_at, importance_score
                        FROM packet_store
                        WHERE created_at BETWEEN $1 AND $2
                        AND NOT ('session_summarized' = ANY(COALESCE(tags, ARRAY[]::text[])))
                        AND importance_score >= $3
                        ORDER BY created_at ASC
                        LIMIT $4
                        """,
                        window_start,
                        cutoff_time,
                        config.min_importance_threshold,
                        config.max_source_items,
                    )
                else:
                    # Get summaries from previous tier
                    prev_tier = (
                        SummaryTier.SESSION
                        if tier == SummaryTier.DAILY
                        else SummaryTier.DAILY
                    )
                    rows = await conn.fetch(
                        """
                        SELECT fact_id, fact_text, importance, created_at
                        FROM semantic_facts
                        WHERE tier = $1
                        AND created_at BETWEEN $2 AND $3
                        AND NOT ('rolled_up' = ANY(COALESCE(tags, ARRAY[]::text[])))
                        ORDER BY importance DESC, created_at ASC
                        LIMIT $4
                        """,
                        prev_tier.value,
                        window_start,
                        cutoff_time,
                        config.max_source_items,
                    )

                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Failed to get unsummarized items: {e}", exc_info=True)
            return []

    def _group_by_time_window(
        self,
        items: list[dict[str, Any]],
        window_minutes: int,
    ) -> dict[datetime, list[dict[str, Any]]]:
        """Group items into time windows."""
        windows: dict[datetime, list[dict[str, Any]]] = {}

        for item in items:
            created_at = item.get("created_at")
            if not created_at:
                continue

            # Round down to window start
            window_start = created_at.replace(
                minute=(created_at.minute // window_minutes) * window_minutes,
                second=0,
                microsecond=0,
            )

            if window_start not in windows:
                windows[window_start] = []
            windows[window_start].append(item)

        return windows

    @must_stay_async("callers use await")
    async def _generate_summary(
        self,
        tier: SummaryTier,
        items: list[dict[str, Any]],
        config: SummaryConfig,
    ) -> SummaryResult | None:
        """Generate a summary using LLM."""
        if not items:
            return None

        # Extract text content
        texts = []
        source_ids = []
        total_chars = 0

        for item in items:
            text = ""
            if "envelope" in item:
                payload = item["envelope"].get("payload", {})
                text = (
                    payload.get("text")
                    or payload.get("content")
                    or payload.get("description")
                    or str(payload)[:500]
                )
                source_ids.append(item.get("packet_id"))
            elif "fact_text" in item:
                text = item["fact_text"]
                source_ids.append(item.get("fact_id"))

            if text:
                texts.append(text)
                total_chars += len(text)

        if not texts:
            return None

        combined_content = "\n\n---\n\n".join(texts)

        # Generate summary via LLM
        summary_text = await self._call_llm(
            config.prompt_template.format(content=combined_content)
        )

        if not summary_text:
            return None

        # Calculate metrics
        compression_ratio = len(summary_text) / total_chars if total_chars > 0 else 0
        avg_importance = sum(
            item.get("importance_score", item.get("importance", 0.5)) for item in items
        ) / len(items)

        return SummaryResult(
            tier=tier,
            source_count=len(items),
            summary_text=summary_text,
            compression_ratio=compression_ratio,
            importance_score=min(
                avg_importance + 0.1, 1.0
            ),  # Boost importance slightly
            source_ids=[s for s in source_ids if s],
            metadata={
                "window_start": (
                    items[0].get("created_at").isoformat() if items else None
                ),
                "total_source_chars": total_chars,
            },
        )

    async def _call_llm(self, prompt: str) -> str | None:
        """Call LLM for summarization."""
        if self._llm_client is None:
            logger.warning("No LLM client configured, using extractive fallback")
            return self._extractive_fallback(prompt)

        try:
            # Try Anthropic client
            if hasattr(self._llm_client, "messages"):
                response = await self._llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text

            # Try OpenAI client
            if hasattr(self._llm_client, "chat"):
                response = await self._llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content

            logger.warning("Unknown LLM client type")
            return self._extractive_fallback(prompt)

        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return self._extractive_fallback(prompt)

    def _extractive_fallback(self, prompt: str) -> str:
        """Fallback extractive summary when LLM unavailable."""
        # Extract content from prompt
        import re

        # Find content block
        match = re.search(r"Requirements:", prompt)
        content = prompt[: match.start()].strip() if match else prompt

        # Simple extractive: first 2-3 sentences per section
        sections = content.split("\n\n---\n\n")
        summaries = []

        for section in sections[:10]:  # Limit sections
            sentences = re.split(r"(?<=[.!?])\s+", section.strip())
            if sentences:
                summaries.append(" ".join(sentences[:2]))

        return "\n".join(summaries[:5])

    async def _store_summary(self, summary: SummaryResult) -> None:
        """Store summary in semantic_facts table."""
        if self._repository is None:
            return

        try:
            await self._repository.insert_semantic_fact(
                fact_text=summary.summary_text,
                triplet={
                    "subject": f"{summary.tier.value}_summary",
                    "predicate": "summarizes",
                    "object": f"{summary.source_count} items",
                },
                importance=summary.importance_score,
                tier=summary.tier.value,
                source="hierarchical_summarizer",
                confidence=0.85,
                tags=[f"summary_{summary.tier.value}", "auto_generated"],
            )

            logger.debug(
                "Stored summary",
                tier=summary.tier.value,
                length=len(summary.summary_text),
            )

        except Exception as e:
            logger.error(f"Failed to store summary: {e}", exc_info=True)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-032",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "debugging",
        "learning",
        "logging",
        "messaging",
        "metrics",
    ],
    "keywords": [
        "cascade",
        "daily",
        "hierarchical",
        "into",
        "memory",
        "summaries",
        "summarizer",
        "summary",
    ],
    "business_value": "Implements tiered memory summarization with 20min → daily → weekly cascade. Part of Stage 2: Hierarchical Memory Consolidation Engine (SUPER-PROMPT). 20-minute summaries: Capture session highlights Da",
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
