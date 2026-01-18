"""
L9 Memory Substrate Client

Async HTTP client for the Memory Substrate API using httpx.
Treats the memory substrate as a black-box service.

Version: 1.0.0
Schema: Memory.yaml v1.0.1

Endpoints:
  - POST /api/v1/memory/packet      → write_packet()
  - POST /api/v1/memory/semantic/search → semantic_search()
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Client",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "integration",
    "domain": "data_models",
    "module_name": "memory_client",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["clients.__init__", "core.singleton_registry", "runtime.l_tools", "services.research.research_graph", "tests.clients.test_memory_client", "tests.memory.test_memory_adapter_basic"],
    },
}
# ============================================================================

import structlog
import os
from typing import Any, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel, Field
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# PRIMARY: VPS Memory API (production)
# FALLBACK: Local Docker l9-api container (for testing when VPS unavailable)
VPS_MEMORY_URL = "http://l9-memory-api:8080"  # VPS production
DOCKER_FALLBACK_URL = "http://l9-api:8000"  # Local Docker fallback

DEFAULT_BASE_URL = VPS_MEMORY_URL
DEFAULT_TIMEOUT = 30.0
FALLBACK_ENABLED = True  # Enable automatic fallback to Docker


# =============================================================================
# Request/Response Models (aligned with Memory.yaml v1.0.1)
# =============================================================================


class PacketEnvelopeIn(BaseModel):
    """
    Input structure for packet writes.

    Based on Memory.yaml v1.0.1 PacketEnvelopeIn schema.
    """

    packet_type: str = Field(
        ..., min_length=1, description="Semantic category (e.g., event, insight)"
    )
    payload: dict[str, Any] = Field(..., description="Flexible JSON-like structure")
    metadata: Optional[dict[str, Any]] = Field(None, description="Optional metadata")
    provenance: Optional[dict[str, Any]] = Field(
        None, description="Optional provenance (parent_packet, source_agent)"
    )
    confidence: Optional[dict[str, Any]] = Field(
        None, description="Optional confidence (score, rationale)"
    )


class PacketWriteResult(BaseModel):
    """
    Response from packet write endpoint.

    Based on Memory.yaml v1.0.1 PacketWriteResult schema.
    """

    status: str = Field(..., description="'ok' or 'error'")
    packet_id: UUID = Field(..., description="Assigned packet ID")
    written_tables: list[str] = Field(
        default_factory=list, description="Tables updated"
    )
    error_message: Optional[str] = Field(
        None, description="Error details if status='error'"
    )


class SemanticSearchRequest(BaseModel):
    """
    Request for semantic search.

    Based on Memory.yaml v1.0.1 SemanticSearchRequest schema.
    """

    query: str = Field(..., min_length=1, description="Natural language query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")


class SemanticHit(BaseModel):
    """Single semantic search result."""

    embedding_id: UUID
    score: float
    payload: dict[str, Any]


class SemanticSearchResult(BaseModel):
    """Response from semantic search endpoint."""

    query: str
    hits: list[SemanticHit] = Field(default_factory=list)


# =============================================================================
# Memory Client
# =============================================================================


class MemoryClient:
    """
    Async HTTP client for L9 Memory Substrate API.

    Primary: VPS Memory API (production)
    Fallback: Local Docker l9-api (when VPS unavailable)

    Usage:
        client = MemoryClient()
        result = await client.write_packet(
            packet_type="insight",
            payload={"summary": "...", "source": "research_graph"},
        )
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        enable_fallback: bool = FALLBACK_ENABLED,
    ):
        """
        Initialize memory client.

        Args:
            base_url: Memory API base URL. Defaults to MEMORY_API_BASE_URL env var
                      or VPS memory API. Falls back to Docker if unavailable.
            timeout: Request timeout in seconds.
            enable_fallback: Enable automatic fallback to Docker when VPS unavailable.
        """
        self.primary_url = base_url or os.getenv("MEMORY_API_BASE_URL", VPS_MEMORY_URL)
        self.fallback_url = os.getenv("MEMORY_API_FALLBACK_URL", DOCKER_FALLBACK_URL)
        self.base_url = self.primary_url  # Start with primary
        self.timeout = timeout
        self.enable_fallback = enable_fallback
        self._client: Optional[httpx.AsyncClient] = None
        self._using_fallback = False

    @must_stay_async("callers use await")
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _try_fallback(self) -> bool:
        """
        Switch to fallback URL (Docker) if not already using it.

        Returns:
            True if switched to fallback, False if already on fallback
        """
        if self._using_fallback or not self.enable_fallback:
            return False

        logger.warning(
            f"VPS Memory API unavailable at {self.primary_url}, "
            f"switching to Docker fallback at {self.fallback_url}"
        )
        self.base_url = self.fallback_url
        self._using_fallback = True

        # Close existing client so new one uses fallback URL
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

        return True

    @property
    def is_using_fallback(self) -> bool:
        """Check if currently using Docker fallback."""
        return self._using_fallback

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @must_stay_async("async context manager protocol")
    async def __aenter__(self) -> "MemoryClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    # =========================================================================
    # API Methods
    # =========================================================================

    async def write_packet(
        self,
        packet_type: str,
        payload: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
        provenance: Optional[dict[str, Any]] = None,
        confidence: Optional[dict[str, Any]] = None,
    ) -> PacketWriteResult:
        """
        Write a packet to the memory substrate.

        POST /api/v1/memory/packet

        Tries VPS first, falls back to Docker if VPS unavailable.

        Args:
            packet_type: Semantic category (e.g., "insight", "event", "research_result")
            payload: Flexible JSON payload
            metadata: Optional metadata (schema_version, agent, domain)
            provenance: Optional provenance (parent_packet, source_agent)
            confidence: Optional confidence (score, rationale)

        Returns:
            PacketWriteResult with status, packet_id, written_tables

        Raises:
            httpx.HTTPStatusError: On HTTP error responses
            httpx.RequestError: On connection/timeout errors (after fallback attempted)
        """
        packet = PacketEnvelopeIn(
            packet_type=packet_type,
            payload=payload,
            metadata=metadata,
            provenance=provenance,
            confidence=confidence,
        )

        logger.debug(f"Writing packet: type={packet_type}")

        # Try primary (VPS), fall back to Docker on connection error
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/memory/packet",
                json=packet.model_dump(exclude_none=True),
            )
            response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            # VPS unavailable - try Docker fallback
            if await self._try_fallback():
                logger.info("Retrying write_packet with Docker fallback")
                client = await self._get_client()
                response = await client.post(
                    "/api/v1/memory/packet",
                    json=packet.model_dump(exclude_none=True),
                )
                response.raise_for_status()
            else:
                raise  # Already on fallback or fallback disabled

        result = PacketWriteResult.model_validate(response.json())
        logger.info(
            f"Packet written: id={result.packet_id}, tables={result.written_tables}"
            f"{' (via Docker fallback)' if self._using_fallback else ''}"
        )

        return result

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        agent_id: Optional[str] = None,
    ) -> SemanticSearchResult:
        """
        Search semantic memory using natural language query.

        POST /api/v1/memory/semantic/search

        Tries VPS first, falls back to Docker if VPS unavailable.

        Args:
            query: Natural language search query
            top_k: Number of results to return (1-100, default 10)
            agent_id: Optional filter by agent ID

        Returns:
            SemanticSearchResult with query and list of hits

        Raises:
            httpx.HTTPStatusError: On HTTP error responses
            httpx.RequestError: On connection/timeout errors (after fallback attempted)
        """
        request = SemanticSearchRequest(
            query=query,
            top_k=top_k,
            agent_id=agent_id,
        )

        logger.debug(f"Semantic search: query={query[:50]}..., top_k={top_k}")

        # Try primary (VPS), fall back to Docker on connection error
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/memory/semantic/search",
                json=request.model_dump(exclude_none=True),
            )
            response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            # VPS unavailable - try Docker fallback
            if await self._try_fallback():
                logger.info("Retrying semantic search with Docker fallback")
                client = await self._get_client()
                response = await client.post(
                    "/api/v1/memory/semantic/search",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()
            else:
                raise  # Already on fallback or fallback disabled

        result = SemanticSearchResult.model_validate(response.json())
        logger.info(
            f"Semantic search returned {len(result.hits)} hits"
            f"{' (via Docker fallback)' if self._using_fallback else ''}"
        )

        return result

    async def health_check(self) -> bool:
        """
        Check if the memory API is healthy.

        Tries VPS first, falls back to Docker if VPS unavailable.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            # VPS unavailable - try Docker fallback
            if await self._try_fallback():
                try:
                    client = await self._get_client()
                    response = await client.get("/health")
                    return response.status_code == 200
                except Exception as e:
                    logger.warning(
                        f"Memory API health check failed (Docker fallback): {e}"
                    )
                    return False
            return False
        except Exception as e:
            logger.warning(f"Memory API health check failed: {e}")
            return False

    # =========================================================================
    # Hybrid Search (v1.1.0+)
    # =========================================================================

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        min_score: float = 0.5,
    ) -> dict[str, Any]:
        """
        Perform hybrid search combining semantic and structured filters.

        POST /api/v1/memory/hybrid/search

        Args:
            query: Natural language search query
            top_k: Number of results to return
            filters: Structured filters (packet_type, tags, date_range)
            agent_id: Optional agent filter
            min_score: Minimum similarity score threshold

        Returns:
            Dict with search results
        """
        client = await self._get_client()

        logger.debug(f"Hybrid search: query={query[:50]}..., filters={filters}")

        response = await client.post(
            "/api/v1/memory/hybrid/search",
            params={
                "query": query,
                "top_k": top_k,
                "agent_id": agent_id,
                "min_score": min_score,
            },
            json=filters or {},
        )
        response.raise_for_status()

        return response.json()

    # =========================================================================
    # Lineage & Thread (v1.1.0+)
    # =========================================================================

    async def fetch_lineage(
        self,
        packet_id: str,
        direction: str = "ancestors",
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Fetch packet lineage graph.

        GET /api/v1/memory/lineage/{packet_id}

        Args:
            packet_id: Starting packet UUID
            direction: "ancestors" or "descendants"
            max_depth: Maximum traversal depth

        Returns:
            Dict with lineage chain
        """
        client = await self._get_client()

        response = await client.get(
            f"/api/v1/memory/lineage/{packet_id}",
            params={"direction": direction, "max_depth": max_depth},
        )
        response.raise_for_status()

        return response.json()

    async def fetch_thread(
        self,
        thread_id: str,
        limit: int = 100,
        order: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch all packets in a conversation thread.

        GET /api/v1/memory/thread/{thread_id}

        Args:
            thread_id: Thread UUID
            limit: Maximum packets to return
            order: "asc" or "desc"

        Returns:
            List of packets in thread order
        """
        client = await self._get_client()

        response = await client.get(
            f"/api/v1/memory/thread/{thread_id}",
            params={"limit": limit, "order": order},
        )
        response.raise_for_status()

        return response.json()

    # =========================================================================
    # Facts & Insights (v1.1.0+)
    # =========================================================================

    async def fetch_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        source_packet: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch knowledge facts.

        GET /api/v1/memory/facts

        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            source_packet: Filter by source packet
            limit: Maximum facts to return

        Returns:
            List of knowledge facts
        """
        client = await self._get_client()

        params = {"limit": limit}
        if subject:
            params["subject"] = subject
        if predicate:
            params["predicate"] = predicate
        if source_packet:
            params["source_packet"] = source_packet

        response = await client.get("/api/v1/memory/facts", params=params)
        response.raise_for_status()

        return response.json()

    async def fetch_insights(
        self,
        packet_id: Optional[str] = None,
        insight_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch extracted insights.

        GET /api/v1/memory/insights

        Args:
            packet_id: Filter by source packet
            insight_type: Filter by insight type
            limit: Maximum insights to return

        Returns:
            List of insights
        """
        client = await self._get_client()

        params = {"limit": limit}
        if packet_id:
            params["packet_id"] = packet_id
        if insight_type:
            params["insight_type"] = insight_type

        response = await client.get("/api/v1/memory/insights", params=params)
        response.raise_for_status()

        return response.json()

    # =========================================================================
    # Garbage Collection (v1.1.0+)
    # =========================================================================

    async def run_gc(self) -> dict[str, Any]:
        """
        Trigger garbage collection cycle.

        POST /api/v1/memory/gc/run

        Returns:
            Dict with GC results
        """
        client = await self._get_client()

        logger.debug("Triggering garbage collection")

        response = await client.post("/api/v1/memory/gc/run")
        response.raise_for_status()

        result = response.json()
        logger.info(f"GC completed: {result}")

        return result

    async def get_gc_stats(self) -> dict[str, Any]:
        """
        Get garbage collection statistics.

        GET /api/v1/memory/gc/stats

        Returns:
            Dict with GC stats
        """
        client = await self._get_client()

        response = await client.get("/api/v1/memory/gc/stats")
        response.raise_for_status()

        return response.json()


# =============================================================================
# Singleton / Factory
# =============================================================================

_client: Optional[MemoryClient] = None


def get_memory_client() -> MemoryClient:
    """
    Get or create singleton MemoryClient instance.

    Returns:
        MemoryClient instance
    """
    global _client
    if _client is None:
        _client = MemoryClient()
    return _client


async def close_memory_client() -> None:
    """Close the singleton memory client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CLI-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "client", "data-models", "debugging", "event-driven", "http-client", "integration", "logging", "messaging", "pydantic"],
    "keywords": ["check", "client", "close", "envelope", "facts", "fallback", "fetch", "health"],
    "business_value": "Provides memory client components including PacketEnvelopeIn, PacketWriteResult, SemanticSearchRequest",
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
