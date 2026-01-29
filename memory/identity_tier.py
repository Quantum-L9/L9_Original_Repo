"""
L9 Memory Substrate - Identity Tier Service
Version: 3.1.0

Implements the Identity Tier for frontier-grade 4-tier hierarchical memory:
- Identity (permanent, immutable core facts)
- Project (working context, scoped)
- Session (ephemeral, temporal)
- General (default tier)

Identity tier facts are:
- Human-curated (validated by Igor or system)
- High importance (0.8+ by default)
- Permanent (no decay, no TTL)
- Core to agent identity (values, preferences, goals)

Based on frontier AI lab patterns (Anthropic, OpenAI, DeepMind).
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Identity Tier Service",
    "module_version": "3.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "identity_tier",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API", "OpenAI API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "memory.__init__",
            "tests.memory.test_frontier_memory_pipeline",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog

if TYPE_CHECKING:
    from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


# =============================================================================
# Constants
# =============================================================================

IDENTITY_TIER = "identity"
IDENTITY_MIN_IMPORTANCE = 0.8
IDENTITY_DEFAULT_CONFIDENCE = 0.9


class IdentityFactSource(str, Enum):
    """Source types for identity tier facts."""

    IGOR_STATED = "igor_stated"  # Human-curated by Igor
    SYSTEM_INFERRED = "system_inferred"  # System-extracted from behavior
    AGENT_LEARNED = "agent_learned"  # Agent self-discovery
    IMPORTED = "imported"  # Imported from external source


class IdentityFactCategory(str, Enum):
    """Categories of identity facts."""

    CORE_VALUE = "core_value"  # Fundamental values and beliefs
    PREFERENCE = "preference"  # Preferences and style choices
    GOAL = "goal"  # Long-term goals and objectives
    CAPABILITY = "capability"  # Skills and capabilities
    CONSTRAINT = "constraint"  # Hard constraints and boundaries
    RELATIONSHIP = "relationship"  # Relationships with entities
    IDENTITY = "identity"  # Self-description and identity


# =============================================================================
# Identity Fact Model
# =============================================================================


@dataclass
class IdentityFact:
    """
    A fact in the Identity Tier.

    Identity facts are permanent, high-importance core knowledge
    that defines the agent's identity, values, and goals.
    """

    fact_id: UUID = field(default_factory=uuid4)
    fact_text: str = ""
    triplet: dict[str, Any] = field(default_factory=dict)

    # Identity-specific fields
    category: IdentityFactCategory = IdentityFactCategory.IDENTITY
    source: IdentityFactSource = IdentityFactSource.IGOR_STATED

    # Always high importance for identity
    importance: float = IDENTITY_MIN_IMPORTANCE
    confidence: float = IDENTITY_DEFAULT_CONFIDENCE

    # Tags for categorization
    tags: list[str] = field(default_factory=list)

    # Validation
    validated_at: datetime | None = None
    validated_by: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Ensure identity facts have minimum importance."""
        if self.importance < IDENTITY_MIN_IMPORTANCE:
            self.importance = IDENTITY_MIN_IMPORTANCE

        # Add identity tier tag
        if "identity" not in self.tags:
            self.tags = ["identity", *list(self.tags)]


# =============================================================================
# Identity Tier Service
# =============================================================================


class IdentityTierService:
    """
    Service for managing Identity Tier facts.

    The Identity Tier is the highest tier in the 4-tier hierarchical memory:
    - Facts are permanent (no decay)
    - Facts are human-curated or system-validated
    - Facts have high importance (0.8+ minimum)
    - Facts define agent identity, values, and goals

    This service provides:
    - CRUD operations for identity facts
    - Validation and curation workflow
    - Context injection for agent prompts
    - Bulk import/export for identity facts
    """

    def __init__(self, repository: SubstrateRepository | None = None):
        """
        Initialize IdentityTierService.

        Args:
            repository: SubstrateRepository instance for database access
        """
        self._repository = repository
        logger.info("IdentityTierService initialized")

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update the repository reference."""
        self._repository = repository

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_identity_fact(
        self,
        fact_text: str,
        triplet: dict[str, Any] | None = None,
        category: IdentityFactCategory = IdentityFactCategory.IDENTITY,
        source: IdentityFactSource = IdentityFactSource.IGOR_STATED,
        tags: list[str] | None = None,
        importance: float = IDENTITY_MIN_IMPORTANCE,
        confidence: float = IDENTITY_DEFAULT_CONFIDENCE,
        validated_by: str | None = None,
        agent_id: str | None = None,
        tenant_id: UUID | None = None,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> UUID:
        """
        Create a new identity tier fact.

        Args:
            fact_text: Human-readable fact statement
            triplet: SPO triplet {"subject": "...", "predicate": "...", "object": "..."}
            category: Fact category (core_value, preference, goal, etc.)
            source: How this fact was obtained
            tags: Additional tags for categorization
            importance: Importance score (minimum 0.8 for identity tier)
            confidence: Confidence in the fact
            validated_by: Who validated this fact (igor, L, system)
            agent_id: Agent that owns this fact
            tenant_id, org_id, user_id: Multi-tenant ownership

        Returns:
            UUID of the created fact
        """
        if self._repository is None:
            raise RuntimeError("Repository not initialized")

        # Enforce minimum importance for identity tier
        if importance < IDENTITY_MIN_IMPORTANCE:
            importance = IDENTITY_MIN_IMPORTANCE
            logger.warning(
                f"Identity fact importance below minimum, elevated to {IDENTITY_MIN_IMPORTANCE}"
            )

        # Build tags list
        fact_tags = ["identity", category.value]
        if tags:
            fact_tags.extend(tags)

        # Set validation if provided
        datetime.now(timezone.utc) if validated_by else None

        # Create fact via repository
        fact_id = await self._repository.insert_semantic_fact(
            fact_text=fact_text,
            triplet=triplet
            or {"subject": fact_text, "predicate": "is", "object": "identity_fact"},
            importance=importance,
            tags=fact_tags,
            tier=IDENTITY_TIER,
            source=source.value,
            confidence=confidence,
            agent_id=agent_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
        )

        logger.info(
            f"Created identity fact: {fact_id}",
            fact_id=str(fact_id),
            category=category.value,
            source=source.value,
        )

        return fact_id

    async def get_identity_facts(
        self,
        category: IdentityFactCategory | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list:
        """
        Get all identity tier facts, optionally filtered by category or tags.

        Args:
            category: Optional category filter
            tags: Optional tags to filter by
            limit: Maximum facts to return

        Returns:
            List of SemanticFactRow objects from identity tier
        """
        if self._repository is None:
            return []

        # Get all identity tier facts
        facts = await self._repository.get_semantic_facts_by_tier(
            tier=IDENTITY_TIER,
            limit=limit,
        )

        # Apply category filter
        if category:
            facts = [f for f in facts if category.value in f.tags]

        # Apply tag filter
        if tags:
            facts = [f for f in facts if any(t in f.tags for t in tags)]

        return facts

    async def get_identity_fact_by_id(self, fact_id: UUID):
        """
        Get a specific identity fact by ID.

        Args:
            fact_id: UUID of the fact

        Returns:
            SemanticFactRow or None
        """
        if self._repository is None:
            return None

        # Use repository method to get by ID
        async with self._repository.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM semantic_facts
                WHERE fact_id = $1 AND tier = $2
                """,
                fact_id,
                IDENTITY_TIER,
            )

        if not row:
            return None

        import json

        from memory.substrate_models import SemanticFactRow

        return SemanticFactRow(
            fact_id=row["fact_id"],
            tenant_id=row["tenant_id"],
            org_id=row["org_id"],
            user_id=row["user_id"],
            agent_id=row.get("agent_id"),
            fact_text=row["fact_text"],
            triplet=(
                row["triplet"]
                if isinstance(row["triplet"], dict)
                else json.loads(row["triplet"] or "{}")
            ),
            importance=row["importance"],
            access_count=row["access_count"],
            last_accessed=row.get("last_accessed"),
            tags=row.get("tags") or [],
            tier=row.get("tier", IDENTITY_TIER),
            source=row.get("source"),
            source_packet_id=row.get("source_packet_id"),
            confidence=row.get("confidence", IDENTITY_DEFAULT_CONFIDENCE),
            validated_at=row.get("validated_at"),
            validated_by=row.get("validated_by"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def validate_identity_fact(
        self,
        fact_id: UUID,
        validated_by: str = "system",
    ) -> bool:
        """
        Mark an identity fact as validated.

        Args:
            fact_id: UUID of the fact to validate
            validated_by: Who validated this fact (igor, L, system)

        Returns:
            True if fact was found and validated
        """
        if self._repository is None:
            return False

        async with self._repository.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE semantic_facts
                SET validated_at = NOW(),
                    validated_by = $2
                WHERE fact_id = $1 AND tier = $3
                """,
                fact_id,
                validated_by,
                IDENTITY_TIER,
            )

        updated = result.split()[-1] != "0"
        if updated:
            logger.info(f"Validated identity fact {fact_id} by {validated_by}")
        return updated

    # =========================================================================
    # Context Injection
    # =========================================================================

    async def get_identity_context(
        self,
        categories: list[IdentityFactCategory] | None = None,
        max_facts: int = 20,
        format_type: str = "markdown",
    ) -> str:
        """
        Get identity tier facts formatted for context injection.

        This is the primary interface for injecting identity facts
        into agent system prompts or context windows.

        Args:
            categories: Optional filter by categories
            max_facts: Maximum number of facts to include
            format_type: Output format ("markdown", "json", "text")

        Returns:
            Formatted string with identity facts for context injection
        """
        facts = await self.get_identity_facts(limit=max_facts)

        # Filter by categories if specified
        if categories:
            category_values = [c.value for c in categories]
            facts = [f for f in facts if any(t in f.tags for t in category_values)]

        if not facts:
            return ""

        # Format based on type
        if format_type == "json":
            import json

            return json.dumps(
                [
                    {
                        "fact": f.fact_text,
                        "importance": f.importance,
                        "category": next(
                            (
                                t
                                for t in f.tags
                                if t in [c.value for c in IdentityFactCategory]
                            ),
                            "identity",
                        ),
                    }
                    for f in facts
                ],
                indent=2,
            )

        if format_type == "text":
            return "\n".join([f"- {f.fact_text}" for f in facts])

        # markdown (default)
        lines = ["## Identity Core Facts\n"]

        # Group by category
        categorized: dict[str, list] = {}
        for f in facts:
            cat = next(
                (t for t in f.tags if t in [c.value for c in IdentityFactCategory]),
                "identity",
            )
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(f)

        for cat, cat_facts in categorized.items():
            lines.append(f"\n### {cat.replace('_', ' ').title()}\n")
            for f in cat_facts:
                lines.append(f"- {f.fact_text}")

        return "\n".join(lines)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def import_identity_facts(
        self,
        facts: list[dict[str, Any]],
        source: IdentityFactSource = IdentityFactSource.IMPORTED,
        validated_by: str = "import",
    ) -> dict[str, Any]:
        """
        Bulk import identity facts.

        Args:
            facts: List of fact dicts with at least 'fact_text'
            source: Source for all imported facts
            validated_by: Who validated these facts

        Returns:
            Dict with import statistics
        """
        created = 0
        skipped = 0
        errors = []

        for fact_data in facts:
            try:
                fact_text = fact_data.get("fact_text") or fact_data.get("text")
                if not fact_text:
                    skipped += 1
                    continue

                category_str = fact_data.get("category", "identity")
                try:
                    category = IdentityFactCategory(category_str)
                except ValueError:
                    category = IdentityFactCategory.IDENTITY

                await self.create_identity_fact(
                    fact_text=fact_text,
                    triplet=fact_data.get("triplet"),
                    category=category,
                    source=source,
                    tags=fact_data.get("tags", []),
                    importance=fact_data.get("importance", IDENTITY_MIN_IMPORTANCE),
                    validated_by=validated_by,
                )
                created += 1

            except Exception as e:
                errors.append(
                    {"fact": fact_data.get("fact_text", "unknown"), "error": str(e)}
                )

        logger.info(
            f"Imported identity facts: {created} created, {skipped} skipped, {len(errors)} errors"
        )

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "total": len(facts),
        }

    async def export_identity_facts(self) -> list[dict[str, Any]]:
        """
        Export all identity facts for backup or transfer.

        Returns:
            List of fact dicts
        """
        facts = await self.get_identity_facts(limit=1000)

        return [
            {
                "fact_id": str(f.fact_id),
                "fact_text": f.fact_text,
                "triplet": f.triplet,
                "importance": f.importance,
                "confidence": f.confidence,
                "tags": f.tags,
                "source": f.source,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in facts
        ]


# =============================================================================
# Singleton / Factory
# =============================================================================


_identity_service: IdentityTierService | None = None


def get_identity_tier_service() -> IdentityTierService:
    """Get or create the IdentityTierService singleton."""
    global _identity_service
    if _identity_service is None:
        _identity_service = IdentityTierService()
    return _identity_service


def init_identity_tier_service(
    repository: SubstrateRepository,
) -> IdentityTierService:
    """Initialize the IdentityTierService with repository."""
    service = get_identity_tier_service()
    service.set_repository(repository)
    return service


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-033",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_models"],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "learning",
        "logging",
        "serialization",
        "service",
    ],
    "keywords": [
        "agent",
        "category",
        "core",
        "create",
        "default",
        "export",
        "fact",
        "facts",
    ],
    "business_value": "Identity (permanent, immutable core facts) Project (working context, scoped) Session (ephemeral, temporal) General (default tier) Human-curated (validated by Igor or system) High importance (0.8+ by d",
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
