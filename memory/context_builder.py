"""
L9 Memory Substrate - Hierarchical Context Builder
Version: 3.1.0

Builds context for agent prompts using 4-tier hierarchical memory:
- Identity (permanent, unchanging) - HIGHEST PRIORITY
- Project (working context, scoped)
- Session (ephemeral, temporal)
- General (default tier) - LOWEST PRIORITY

Context injection follows tier precedence:
1. Identity facts are ALWAYS included first
2. Project facts are included if project_id is set
3. Session facts are included based on recency
4. General facts fill remaining token budget

Based on frontier AI lab patterns (Anthropic, OpenAI, DeepMind).
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = structlog.get_logger(__name__)


# =============================================================================
# Memory Tier Enum
# =============================================================================


class MemoryTier(str, Enum):
    """
    4-tier hierarchical memory system.

    Tiers are ordered by precedence (highest to lowest):
    1. IDENTITY - Core facts, values, goals (permanent)
    2. PROJECT - Project-specific context (scoped)
    3. SESSION - Conversation context (ephemeral)
    4. GENERAL - Default tier (standard decay)
    """

    IDENTITY = "identity"
    PROJECT = "project"
    SESSION = "session"
    GENERAL = "general"

    @property
    def precedence(self) -> int:
        """Get numeric precedence (higher = more important)."""
        return {
            MemoryTier.IDENTITY: 4,
            MemoryTier.PROJECT: 3,
            MemoryTier.SESSION: 2,
            MemoryTier.GENERAL: 1,
        }[self]


# =============================================================================
# Context Section
# =============================================================================


@dataclass
class ContextSection:
    """
    A section of context from a specific memory tier.
    """

    tier: MemoryTier
    content: str
    facts: list[dict[str, Any]] = field(default_factory=list)
    token_count: int = 0
    fact_count: int = 0

    def __post_init__(self):
        if not self.token_count and self.content:
            # Rough token estimate (4 chars per token)
            self.token_count = len(self.content) // 4


# =============================================================================
# Hierarchical Context Builder
# =============================================================================


class HierarchicalContextBuilder:
    """
    Builds hierarchical context for agent prompts.

    Follows tier precedence (Identity > Project > Session > General)
    with token budget management.

    Usage:
        builder = HierarchicalContextBuilder(repository)
        context = await builder.build_context(
            project_id="my-project",
            session_id="current-session",
            max_tokens=4000,
        )
    """

    # Token allocation by tier (percentages of max_tokens)
    DEFAULT_ALLOCATION = {
        MemoryTier.IDENTITY: 0.20,  # 20% for identity
        MemoryTier.PROJECT: 0.35,  # 35% for project
        MemoryTier.SESSION: 0.30,  # 30% for session
        MemoryTier.GENERAL: 0.15,  # 15% for general
    }

    def __init__(
        self,
        repository=None,
        identity_service=None,
        allocation: Optional[dict[MemoryTier, float]] = None,
    ):
        """
        Initialize HierarchicalContextBuilder.

        Args:
            repository: SubstrateRepository instance
            identity_service: IdentityTierService instance
            allocation: Custom token allocation by tier
        """
        self._repository = repository
        self._identity_service = identity_service
        self._allocation = allocation or self.DEFAULT_ALLOCATION
        logger.info("HierarchicalContextBuilder initialized")

    def set_repository(self, repository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    def set_identity_service(self, service) -> None:
        """Set or update the identity service reference."""
        self._identity_service = service

    # =========================================================================
    # Context Building
    # =========================================================================

    async def build_context(
        self,
        project_id: Optional[str] = None,
        session_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        max_tokens: int = 4000,
        include_tiers: Optional[list[MemoryTier]] = None,
        format_type: str = "markdown",
    ) -> str:
        """
        Build hierarchical context from all memory tiers.

        Args:
            project_id: Optional project filter
            session_id: Optional session filter
            agent_id: Optional agent filter
            max_tokens: Maximum tokens for context
            include_tiers: Optional list of tiers to include (default: all)
            format_type: Output format ("markdown", "json", "text")

        Returns:
            Formatted context string respecting tier precedence
        """
        sections: list[ContextSection] = []

        # Determine which tiers to include
        tiers = include_tiers or list(MemoryTier)

        # Build sections in precedence order
        for tier in sorted(tiers, key=lambda t: t.precedence, reverse=True):
            tier_budget = int(max_tokens * self._allocation.get(tier, 0.1))

            if tier == MemoryTier.IDENTITY:
                section = await self._build_identity_section(tier_budget)
            elif tier == MemoryTier.PROJECT:
                section = await self._build_project_section(project_id, tier_budget)
            elif tier == MemoryTier.SESSION:
                section = await self._build_session_section(session_id, tier_budget)
            else:  # GENERAL
                section = await self._build_general_section(agent_id, tier_budget)

            if section and section.content:
                sections.append(section)

        # Format output
        return self._format_context(sections, format_type)

    async def _build_identity_section(self, max_tokens: int) -> ContextSection:
        """Build identity tier context section."""
        if not self._identity_service:
            return ContextSection(tier=MemoryTier.IDENTITY, content="", facts=[])

        # Get identity context
        content = await self._identity_service.get_identity_context(
            max_facts=max_tokens // 50,  # Rough estimate: 50 tokens per fact
            format_type="text",
        )

        facts = await self._identity_service.get_identity_facts(limit=max_tokens // 50)

        return ContextSection(
            tier=MemoryTier.IDENTITY,
            content=content,
            facts=[
                {"fact_text": f.fact_text, "importance": f.importance} for f in facts
            ],
            fact_count=len(facts),
        )

    async def _build_project_section(
        self,
        project_id: Optional[str],
        max_tokens: int,
    ) -> ContextSection:
        """Build project tier context section."""
        if not project_id or not self._repository:
            return ContextSection(tier=MemoryTier.PROJECT, content="", facts=[])

        # Get project-scoped facts
        facts = await self._repository.get_semantic_facts_by_tier(
            tier="project",
            limit=max_tokens // 50,
        )

        # Filter by project_id in tags if applicable
        project_facts = [f for f in facts if project_id in f.tags or not f.tags]

        if not project_facts:
            return ContextSection(tier=MemoryTier.PROJECT, content="", facts=[])

        content = "\n".join([f"- {f.fact_text}" for f in project_facts])

        return ContextSection(
            tier=MemoryTier.PROJECT,
            content=content,
            facts=[
                {"fact_text": f.fact_text, "importance": f.importance}
                for f in project_facts
            ],
            fact_count=len(project_facts),
        )

    async def _build_session_section(
        self,
        session_id: Optional[UUID],
        max_tokens: int,
    ) -> ContextSection:
        """Build session tier context section."""
        if not self._repository:
            return ContextSection(tier=MemoryTier.SESSION, content="", facts=[])

        # Get recent session facts (last 24 hours)
        facts = await self._repository.get_semantic_facts_by_tier(
            tier="session",
            limit=max_tokens // 50,
        )

        # Filter by recency
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_facts = [f for f in facts if f.created_at and f.created_at > cutoff]

        if not recent_facts:
            return ContextSection(tier=MemoryTier.SESSION, content="", facts=[])

        content = "\n".join([f"- {f.fact_text}" for f in recent_facts])

        return ContextSection(
            tier=MemoryTier.SESSION,
            content=content,
            facts=[
                {"fact_text": f.fact_text, "importance": f.importance}
                for f in recent_facts
            ],
            fact_count=len(recent_facts),
        )

    async def _build_general_section(
        self,
        agent_id: Optional[str],
        max_tokens: int,
    ) -> ContextSection:
        """Build general tier context section."""
        if not self._repository:
            return ContextSection(tier=MemoryTier.GENERAL, content="", facts=[])

        # Get general facts (highest importance first)
        facts = await self._repository.get_semantic_facts_by_tier(
            tier="general",
            limit=max_tokens // 50,
        )

        if not facts:
            return ContextSection(tier=MemoryTier.GENERAL, content="", facts=[])

        content = "\n".join([f"- {f.fact_text}" for f in facts])

        return ContextSection(
            tier=MemoryTier.GENERAL,
            content=content,
            facts=[
                {"fact_text": f.fact_text, "importance": f.importance} for f in facts
            ],
            fact_count=len(facts),
        )

    def _format_context(
        self,
        sections: list[ContextSection],
        format_type: str,
    ) -> str:
        """Format context sections into output string."""
        if not sections:
            return ""

        if format_type == "json":
            import json

            return json.dumps(
                {
                    "tiers": [
                        {
                            "tier": s.tier.value,
                            "facts": s.facts,
                            "fact_count": s.fact_count,
                        }
                        for s in sections
                    ]
                },
                indent=2,
            )

        elif format_type == "text":
            return "\n\n".join([s.content for s in sections if s.content])

        else:  # markdown (default)
            lines = ["# Memory Context\n"]

            for section in sections:
                if not section.content:
                    continue

                tier_name = section.tier.value.title()
                lines.append(f"\n## {tier_name} Tier ({section.fact_count} facts)\n")
                lines.append(section.content)

            return "\n".join(lines)

    # =========================================================================
    # Quick Access Methods
    # =========================================================================

    async def get_identity_only(self, max_facts: int = 20) -> str:
        """
        Get only identity tier context.

        Shortcut for when only core identity facts are needed.
        """
        if not self._identity_service:
            return ""

        return await self._identity_service.get_identity_context(max_facts=max_facts)

    async def get_tier_summary(self) -> dict[str, int]:
        """
        Get summary of facts per tier.

        Returns:
            Dict mapping tier name to fact count
        """
        summary = {}

        if self._repository:
            for tier in MemoryTier:
                facts = await self._repository.get_semantic_facts_by_tier(
                    tier=tier.value,
                    limit=1000,
                )
                summary[tier.value] = len(facts)

        return summary


# =============================================================================
# Singleton / Factory
# =============================================================================


_context_builder: Optional[HierarchicalContextBuilder] = None


def get_context_builder() -> HierarchicalContextBuilder:
    """Get or create the HierarchicalContextBuilder singleton."""
    global _context_builder
    if _context_builder is None:
        _context_builder = HierarchicalContextBuilder()
    return _context_builder


def init_context_builder(
    repository,
    identity_service=None,
) -> HierarchicalContextBuilder:
    """Initialize the HierarchicalContextBuilder with dependencies."""
    builder = get_context_builder()
    builder.set_repository(repository)
    if identity_service:
        builder.set_identity_service(identity_service)
    return builder
