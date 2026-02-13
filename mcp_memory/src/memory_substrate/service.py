"""Memory Substrate Service Interface.

Abstract interface for all memory substrate implementations.
Kernel depends ONLY on this interface.

Memory Substrate is responsible for:
  1. Vector embeddings and semantic search
  2. Temporal operations (TTL, decay)
  3. Semantic memory storage/retrieval
  4. Memory lifecycle management
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Service",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T06:01:00Z",
    "updated_at": "2026-01-25T08:58:44Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "service",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from abc import (  # noqa: ADR-0026 - ABC provides shared implementation
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class SubstrateConfig:
    """Configuration for substrate."""

    embedding_provider: str
    embedding_model: str
    db_url: str
    vector_dims: int = 1536
    timeout_seconds: int = 30


@dataclass(frozen=True)
class MemoryRecord:
    """Result from memory search."""

    memory_id: str
    content: str
    kind: str
    scope: str
    importance: float
    confidence: float
    similarity: float
    created_at: datetime
    updated_at: datetime
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AbstractMemoryRepository(ABC):
    """Abstract repository for memory operations."""

    @abstractmethod
    async def save_memory(
        self,
        user_id: str,
        content: str,
        kind: str,
        scope: str,
        duration: str,
    ) -> str:
        """Save memory. Returns memory ID."""
        pass

    @abstractmethod
    async def search_memory(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[MemoryRecord]:
        """Search memory semantically."""
        pass

    @abstractmethod
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete memory. Returns True if deleted."""
        pass

    @abstractmethod
    async def apply_temporal_decay(
        self,
        user_id: str,
        dry_run: bool = True,
    ) -> dict[str, int]:
        """Apply temporal decay. Returns stats."""
        pass

    @abstractmethod
    async def get_stats(self, user_id: str) -> dict[str, Any]:
        """Get memory statistics."""
        pass


class SubstrateService(ABC):
    """Main interface for Memory Substrate."""

    @abstractmethod
    async def initialize(self, config: SubstrateConfig) -> None:
        """Initialize substrate."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections."""
        pass

    @abstractmethod
    def get_repository(self) -> AbstractMemoryRepository:
        """Get memory repository."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if healthy."""
        pass


__all__ = [
    "AbstractMemoryRepository",
    "MemoryRecord",
    "SubstrateConfig",
    "SubstrateService",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-access",
        "dataclass",
        "integration",
        "mcp-integration",
        "service",
    ],
    "keywords": [
        "abstract",
        "apply",
        "check",
        "close",
        "decay",
        "delete",
        "health",
        "initialize",
    ],
    "business_value": "Provides service components including SubstrateConfig, MemoryRecord, AbstractMemoryRepository",
    "last_modified": "2026-01-25T08:58:44Z",
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
