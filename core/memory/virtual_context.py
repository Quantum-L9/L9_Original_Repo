"""
Virtual Context Management

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
Purpose: MemGPT-style virtual context with automatic tier management.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Virtual Context",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "virtual_context",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": ["api.server", "tests.memory.test_consolidation_graph"],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class MemoryTier(Enum):
    """Memory organization tiers (like OS virtual memory)"""

    MAIN_CONTEXT = "main"  # Always loaded (system + recent)
    WORKING_MEMORY = "working"  # Current task context
    ARCHIVAL_MEMORY = "archival"  # Long-term storage (on-demand)


@dataclass
class Memory:
    """Single memory chunk"""

    id: str
    agent_id: str
    content: str
    tier: MemoryTier
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    semantic_importance: float = 0.5  # 0-1 (for eviction)


@dataclass
class Context:
    """Agent execution context (main + working loaded, archival on-demand)"""

    agent_id: str
    task_id: str
    main_context: list[Memory]
    working_memory: list[Memory]
    archival_memory: list[Memory] | None = None


class VirtualContextManager:
    """MemGPT-style virtual context with automatic tier management"""

    def __init__(
        self,
        substrate_service: MemorySubstrateService,
        llm_service: Any = None,
        neo4j_driver: Any = None,
        main_context_size: int = 4096,
        working_memory_size: int = 8192,
    ):
        """
        Initializes a VirtualContextManager for MemGPT-style virtual context with automatic tier management.

        Args:
            substrate_service: Service managing in-memory substrate for context storage.
            llm_service: Language model service used for context processing.
            neo4j_driver: Driver for graph database interactions.
            main_context_size: Size limit for primary context storage.
            working_memory_size: Size limit for working memory tier.
        """
        self.substrate = substrate_service
        self.llm = llm_service
        self.neo4j_driver = neo4j_driver
        self.main_context_size = main_context_size
        self.working_memory_size = working_memory_size
        self.metrics = {
            "contexts_loaded": 0,
            "page_faults": 0,
            "evictions": 0,
            "consolidations": 0,
        }

    async def load_context(
        self,
        agent_id: str,
        task_id: str,
    ) -> Context:
        """Load context for agent execution (main + working only)"""

        try:
            # Load main context (system instructions + recent memories)
            main_context = await self._load_tier(
                agent_id,
                MemoryTier.MAIN_CONTEXT,
                limit=self.main_context_size // 50,
            )

            # Load working memory (current task context)
            working_memory = await self._load_tier(
                agent_id,
                MemoryTier.WORKING_MEMORY,
                limit=self.working_memory_size // 50,
                task_id=task_id,
            )

            context = Context(
                agent_id=agent_id,
                task_id=task_id,
                main_context=main_context,
                working_memory=working_memory,
                archival_memory=None,
            )

            self.metrics["contexts_loaded"] += 1
            logger.info(
                "Loaded context",
                agent_id=agent_id,
                main_count=len(main_context),
                working_count=len(working_memory),
            )
            return context

        except Exception as e:
            logger.error("Failed to load context", error=str(e))
            raise

    async def page_fault_handler(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[Memory]:
        """Retrieve from archival when agent needs it (like OS page fault)"""

        try:
            if hasattr(self.substrate, "memory_search"):
                results = await self.substrate.memory_search(
                    agent_id=agent_id,
                    query=query,
                    limit=limit,
                )
            else:
                results = []

            self.metrics["page_faults"] += 1
            logger.info(
                "Page fault resolved",
                agent_id=agent_id,
                results=len(results) if results else 0,
            )
            return results or []

        except Exception as e:
            logger.error("Page fault error", error=str(e))
            return []

    async def evict_to_archival(
        self,
        agent_id: str,
        context: Context,
        strategy: str = "lru",
    ) -> None:
        """Move old memories to archival tier"""

        try:
            if strategy == "semantic" and self.llm is not None:
                await self._evict_semantic(context)
            else:
                await self._evict_lru(context)

            self.metrics["evictions"] += 1

        except Exception as e:
            logger.error("Eviction error", error=str(e))

    async def _evict_lru(self, context: Context) -> None:
        """Simple LRU: move oldest 50% to archival"""

        memories_by_age = sorted(
            context.main_context,
            key=lambda m: m.created_at,
            reverse=True,
        )

        cutoff = len(memories_by_age) // 2
        to_archive = memories_by_age[cutoff:]

        for memory in to_archive:
            if hasattr(self.substrate, "update_memory_tier"):
                await self.substrate.update_memory_tier(
                    memory_id=memory.id,
                    new_tier=MemoryTier.ARCHIVAL_MEMORY,
                )

        logger.info("LRU eviction complete", archived=len(to_archive))

    async def _evict_semantic(self, context: Context) -> None:
        """
        LLM-driven semantic eviction: keep most relevant memories.

        Uses LLM to score each memory's importance and relevance,
        archiving the lowest-scored 50% instead of purely oldest.
        """
        if not context.main_context:
            return

        # Build memory summaries for LLM
        memory_summaries = []
        for i, mem in enumerate(context.main_context):
            summary = f"[{i}] ({mem.created_at}): {mem.content[:200]}..."
            memory_summaries.append(summary)

        eviction_prompt = f"""You are a memory management system. Given these memories, identify which should be ARCHIVED (less important) vs KEPT (more important).

Consider:
- Recency: Recent memories are usually more relevant
- Importance: Facts, decisions, user preferences are important
- Redundancy: Duplicate information can be archived
- Actionability: Task-related memories should stay

MEMORIES:
{chr(10).join(memory_summaries)}

Return a comma-separated list of memory indices to ARCHIVE (the less important half).
Example response: 0, 3, 5, 7

Respond with ONLY the indices to archive:"""

        try:
            response = await self.llm.complete(eviction_prompt)
            # Parse indices from response
            indices_text = response.strip()
            indices_to_archive = [
                int(idx.strip())
                for idx in indices_text.split(",")
                if idx.strip().isdigit()
            ]

            # Archive selected memories
            archived_count = 0
            for idx in indices_to_archive:
                if 0 <= idx < len(context.main_context):
                    memory = context.main_context[idx]
                    if hasattr(self.substrate, "update_memory_tier"):
                        await self.substrate.update_memory_tier(
                            memory_id=memory.id,
                            new_tier=MemoryTier.ARCHIVAL_MEMORY,
                        )
                        archived_count += 1

            logger.info(
                "Semantic eviction complete",
                archived=archived_count,
                total=len(context.main_context),
            )

        except Exception as e:
            logger.warning(
                "Semantic eviction failed, falling back to LRU",
                error=str(e),
            )
            await self._evict_lru(context)

    async def _load_tier(
        self,
        agent_id: str,
        tier: MemoryTier,
        limit: int,
        task_id: str | None = None,
    ) -> list[Memory]:
        """
        Load memories from specific tier.

        Note: Tier filtering is not yet implemented in the substrate service.
        Currently returns all memories for agent_id regardless of tier.
        TODO: Add tier filter when substrate.memory_search supports filters parameter.
        """
        try:
            if hasattr(self.substrate, "memory_search"):
                # TODO: Pass tier filter when available:
                # filters={"tier": tier.value}
                results = await self.substrate.memory_search(
                    agent_id=agent_id,
                    limit=limit,
                )
                return results or []
            return []

        except Exception as e:
            logger.error("Failed to load tier", tier=tier.value, error=str(e))
            return []

    def get_metrics(self) -> dict:
        """
        Initializes MemoryConsolidationService with virtual context management capabilities for automatic memory tiering and consolidation.
        Args:
            substrate_service: Service managing persistent memory substrate interactions.
            llm_service: Optional language model service for fact extraction and reasoning.
            neo4j_driver: Optional driver for graph database operations within memory context.
        """
        """Get virtual context metrics"""
        return self.metrics


class MemoryConsolidationService:
    """Automatic memory consolidation"""

    def __init__(
        self,
        substrate_service: MemorySubstrateService,
        llm_service: Any = None,
        neo4j_driver: Any = None,
    ):
        """
        Initializes MemoryConsolidationService with virtual context management capabilities for automatic memory tiering and consolidation.

        Args:
            substrate_service: Service managing persistent memory substrate interactions.
            llm_service: Optional language model service for fact extraction and reasoning.
            neo4j_driver: Optional Neo4j driver for graph-based memory operations.
        """
        self.substrate = substrate_service
        self.llm = llm_service
        self.neo4j_driver = neo4j_driver
        self.metrics = {
            "facts_extracted": 0,
            "consolidations": 0,
        }

    async def consolidate(
        self,
        agent_id: str,
        conversation_text: str,
    ) -> None:
        """Extract and consolidate memories from conversation"""

        try:
            # LLM-driven extraction with heuristic fallback
            facts = await self._extract_facts(conversation_text)
            self.metrics["facts_extracted"] += len(facts)

            # Store facts
            if hasattr(self.substrate, "write_memories"):
                await self.substrate.write_memories(agent_id, facts)

            self.metrics["consolidations"] += 1
            logger.info(
                "Consolidation complete",
                agent_id=agent_id,
                facts=len(facts),
            )

        except Exception as e:
            logger.error("Consolidation error", error=str(e))

    async def _extract_facts(self, text: str) -> list[str]:
        """
        Extract facts from conversation using LLM or fallback heuristics.

        LLM-driven extraction identifies:
        - User preferences and corrections
        - Important decisions and learnings
        - Factual statements worth preserving
        """
        if self.llm is not None:
            return await self._llm_extract_facts(text)
        return self._simple_extract(text)

    async def _llm_extract_facts(self, text: str) -> list[str]:
        """LLM-driven fact extraction for high-quality consolidation."""
        extraction_prompt = f"""Extract the most important FACTS from this conversation that should be remembered long-term.

Focus on:
1. User preferences (e.g., "I prefer X over Y")
2. Corrections (e.g., "Actually, the correct way is...")
3. Important decisions (e.g., "We decided to use X")
4. Learnings (e.g., "I learned that X")
5. Key facts (e.g., "The API endpoint is X")

CONVERSATION:
{text[:4000]}  # Limit to avoid token overflow

Return each fact on a new line. Maximum 10 facts.
Facts only, no explanations or numbering."""

        try:
            response = await self.llm.complete(extraction_prompt)
            facts = [
                line.strip()
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 10
            ]
            logger.info("LLM fact extraction complete", facts=len(facts))
            return facts[:10]

        except Exception as e:
            logger.warning("LLM extraction failed, using heuristic", error=str(e))
            return self._simple_extract(text)

    def _simple_extract(self, text: str) -> list[str]:
        """Fallback: Simple fact extraction using heuristics."""
        sentences = text.split(".")
        facts = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(
                kw in sentence.lower()
                for kw in [
                    "is",
                    "are",
                    "was",
                    "were",
                    "should",
                    "must",
                    "will",
                    "prefer",
                    "want",
                    "need",
                    "like",
                    "use",
                ]
            ):
                facts.append(sentence)

        return facts[:10]  # Limit to top 10

    async def consolidate_graph_state(
        self,
        agent_id: str = "L",
    ) -> dict:
        """
        Consolidate graph state into memory (UKG Phase 5).

        This method:
        1. Loads agent state from Neo4j Graph State
        2. Creates a snapshot of responsibilities, directives, tools
        3. Stores the snapshot in consolidation output

        Args:
            agent_id: Agent to consolidate (default "L")

        Returns:
            dict with consolidation results
        """
        try:
            from core.agents.graph_state import AgentGraphLoader

            if self.neo4j_driver is None:
                logger.warning("Neo4j driver not configured for consolidation")
                return {"status": "NOT_CONFIGURED", "agent_id": agent_id}

            loader = AgentGraphLoader(self.neo4j_driver)
            graph_state = await loader.load(
                agent_id
            )  # Returns AgentGraphState dataclass

            if not graph_state:
                logger.warning(f"No graph state found for agent {agent_id}")
                return {"status": "NOT_FOUND", "agent_id": agent_id}

            # Create snapshot (graph_state is AgentGraphState dataclass)
            snapshot = {
                "agent_id": agent_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "responsibilities": [r.title for r in graph_state.responsibilities],
                "directives_count": len(graph_state.directives),
                "tools_count": len(graph_state.tools),
                "designation": graph_state.designation,
                "status": graph_state.status,
            }

            # Store as a consolidation fact
            fact = (
                f"Agent {agent_id} graph state snapshot: "
                f"{snapshot['directives_count']} directives, "
                f"{snapshot['tools_count']} tools, "
                f"responsibilities: {', '.join(snapshot['responsibilities'][:5])}"
            )

            if hasattr(self.substrate, "write_memories"):
                await self.substrate.write_memories(agent_id, [fact])

            self.metrics["consolidations"] += 1
            if "graph_state_snapshots" not in self.metrics:
                self.metrics["graph_state_snapshots"] = 0
            self.metrics["graph_state_snapshots"] += 1

            logger.info(
                "Graph state consolidated",
                agent_id=agent_id,
                directives=snapshot["directives_count"],
                tools=snapshot["tools_count"],
            )

            return {
                "status": "SUCCESS",
                "snapshot": snapshot,
            }

        except ImportError:
            logger.warning("AgentGraphLoader not available for graph consolidation")
            return {"status": "UNAVAILABLE", "agent_id": agent_id}
        except Exception as e:
            logger.error(f"Graph state consolidation failed: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    def get_metrics(self) -> dict:
        """Get consolidation metrics"""
        return self.metrics


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-024",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.graph_state", "memory.substrate_service"],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "foundation",
        "graph-db",
        "logging",
        "metrics",
        "service",
    ],
    "keywords": [
        "archival",
        "consolidate",
        "consolidation",
        "evict",
        "fault",
        "graph",
        "handler",
        "load",
    ],
    "business_value": "Provides virtual context components including MemoryTier, Memory, Context",
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
