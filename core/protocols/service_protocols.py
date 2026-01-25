"""
L9 High-Level Service Protocols
================================

High-level service abstractions that complement fine-grained protocols.

These protocols provide unified interfaces for agents, hiding the complexity
of multiple backend systems (Redis, Neo4j, PostgreSQL, pgvector, LLM providers).

Architecture:
- Fine-grained: CacheClient, GraphClient, VectorStore, MemoryRepository
- High-level: MemoryService (wraps fine-grained), LLMService, GovernanceService

Version: 1.0.0
GMP: GMP-114-high-level-service-protocols
Source: PR #49 (ADR Enforcement Infrastructure)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "High-Level Service Protocols",
    "module_version": "1.0.0",
    "created_by": "GMP-114",
    "created_at": "2026-01-24T00:00:00Z",
    "updated_at": "2026-01-24T00:00:00Z",
    "layer": "foundation",
    "domain": "abstractions",
    "module_name": "service_protocols",
    "type": "protocol",
    "status": "active",
    "adr": ["ADR-0026"],
    "source": "PR #49",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis", "Neo4j", "PostgreSQL", "OpenAI", "Anthropic"],
        "memory_layers": ["semantic_memory", "working_memory", "episodic_memory"],
        "imported_by": [
            "core.protocols.__init__",
            "core.di.container",
        ],
    },
}
# ============================================================================

from typing import Any, Protocol, runtime_checkable

# =============================================================================
# MemoryService - Unified Memory Interface
# =============================================================================


@runtime_checkable
class MemoryService(Protocol):
    """
    High-level protocol for unified memory operations.

    Wraps fine-grained protocols (CacheClient, GraphClient, VectorStore,
    MemoryRepository) into a single interface for agents.

    Example implementations:
    - MemorySubstrateService: Production implementation
    - MockMemoryService: Testing implementation

    Usage:
        class MyAgent:
            def __init__(self, memory: MemoryService):
                self.memory = memory

            async def remember(self, content: str):
                return await self.memory.store(content, session_id="...")
    """

    async def store(
        self,
        content: str,
        *,
        session_id: str,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store content in memory.

        Internally handles:
        - PostgreSQL packet storage
        - Redis hot cache
        - pgvector embedding indexing
        - Neo4j relationship creation

        Args:
            content: Content to store
            session_id: Session identifier
            agent_id: Optional agent identifier
            metadata: Optional metadata dict

        Returns:
            Memory ID of stored content
        """
        ...

    async def retrieve(
        self,
        memory_id: str,
        *,
        session_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve content by memory ID.

        Args:
            memory_id: Memory identifier
            session_id: Session identifier

        Returns:
            Memory content dict or None if not found
        """
        ...

    async def search(
        self,
        query: str,
        *,
        session_id: str,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Search memory using semantic similarity.

        Internally uses pgvector for embedding-based search.

        Args:
            query: Search query
            session_id: Session identifier
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of matching memory items with similarity scores
        """
        ...


# =============================================================================
# LLMService - Unified LLM Interface
# =============================================================================


@runtime_checkable
class LLMService(Protocol):
    """
    High-level protocol for LLM operations.

    Abstracts away provider-specific APIs (OpenAI, Anthropic, local models).

    Example implementations:
    - OpenAILLMService: OpenAI GPT models
    - AnthropicLLMService: Anthropic Claude models
    - LocalLLMService: Local/self-hosted models
    - MockLLMService: Testing implementation

    Usage:
        class MyAgent:
            def __init__(self, llm: LLMService):
                self.llm = llm

            async def think(self, prompt: str) -> str:
                return await self.llm.complete(prompt)
    """

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            model: Model identifier (provider-specific, uses default if None)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        ...

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model identifier (uses default if None)
            temperature: Sampling temperature

        Returns:
            Generated response text
        """
        ...

    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """
        Generate text embedding vector.

        Args:
            text: Input text to embed
            model: Embedding model identifier (uses default if None)

        Returns:
            Embedding vector as list of floats
        """
        ...


# =============================================================================
# GovernanceService - Unified Policy Interface
# =============================================================================


@runtime_checkable
class GovernanceService(Protocol):
    """
    High-level protocol for governance and policy enforcement.

    Centralizes policy checks, rate limiting, and approval workflows.

    Example implementations:
    - GovernanceEngine: Production implementation
    - MockGovernanceService: Testing (always allows)

    Usage:
        class MyAgent:
            def __init__(self, governance: GovernanceService):
                self.governance = governance

            async def execute_tool(self, tool_name: str):
                if await self.governance.check_policy("tool_execution", tool=tool_name):
                    # proceed with execution
                    pass
    """

    async def check_policy(
        self,
        action: str,
        *,
        agent_id: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Check if action is allowed by governance policy.

        Args:
            action: Action identifier (e.g., "tool_execution", "memory_write")
            agent_id: Agent requesting the action
            context: Additional context for policy evaluation

        Returns:
            True if allowed, False if denied
        """
        ...

    async def enforce_limits(
        self,
        resource: str,
        *,
        agent_id: str,
        amount: float = 1.0,
    ) -> bool:
        """
        Enforce resource consumption limits (rate limiting).

        Args:
            resource: Resource type ("tokens", "api_calls", "memory_writes")
            agent_id: Agent consuming the resource
            amount: Amount to consume (default 1.0)

        Returns:
            True if within limits (consumption recorded), False if limit exceeded
        """
        ...

    async def request_approval(
        self,
        action: str,
        *,
        agent_id: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Request approval for high-risk action.

        Args:
            action: Action requiring approval
            agent_id: Agent requesting approval
            reason: Justification for the request
            context: Additional context

        Returns:
            Approval request ID for tracking
        """
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "GovernanceService",
    "LLMService",
    "MemoryService",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-122",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "caching",
        "core",
        "foundation",
        "messaging",
        "mocking",
        "service",
        "testing",
    ],
    "keywords": [
        "approval",
        "chat",
        "check",
        "complete",
        "embed",
        "enforce",
        "execute",
        "fine",
    ],
    "business_value": "Provides service protocols components including MemoryService, LLMService, GovernanceService",
    "last_modified": "2026-01-24T15:21:11Z",
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
