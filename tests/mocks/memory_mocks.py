"""
Memory Mock Implementations
===========================

Mock implementations for memory substrate testing.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Mocks",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "tests",
    "module_name": "memory_mocks",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "S3"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["tests.mocks.__init__"],
    },
}
# ============================================================================

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class MockBlobStore:
    """Mock blob storage for large content."""

    blobs: dict[str, bytes] = field(default_factory=dict)

    def store(self, content: str | bytes) -> str:
        """Store content and return blob ID."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        blob_id = hashlib.sha256(content).hexdigest()[:16]
        self.blobs[blob_id] = content
        return blob_id

    def retrieve(self, blob_id: str) -> bytes | None:
        """Retrieve blob by ID."""
        return self.blobs.get(blob_id)

    def delete(self, blob_id: str) -> bool:
        """Delete blob by ID."""
        if blob_id in self.blobs:
            del self.blobs[blob_id]
            return True
        return False


class MockMemoryAdapter:
    """
    Mock Memory Adapter for testing.

    Simulates the memory substrate without requiring actual database connections.
    """

    def __init__(
        self,
        max_vectors: int = 25000,
        blob_threshold_kb: int = 512,
    ):
        self.max_vectors = max_vectors
        self.blob_threshold_kb = blob_threshold_kb
        self.packets: dict[str, dict[str, Any]] = {}
        self.vectors: list[dict[str, Any]] = []
        self.blob_store = MockBlobStore()
        self.checkpoints: dict[str, dict[str, Any]] = {}

    @must_stay_async("callers use await")
    async def store_blob(self, content: str | bytes) -> str:
        """
        Store large content as a blob.

        Args:
            content: Content to store

        Returns:
            Blob ID
        """
        return self.blob_store.store(content)

    @must_stay_async("callers use await")
    async def retrieve_blob(self, blob_id: str) -> bytes | None:
        """Retrieve blob by ID."""
        return self.blob_store.retrieve(blob_id)

    @must_stay_async("callers use await")
    async def ingest(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Ingest a packet into memory.

        Args:
            data: Packet data to ingest

        Returns:
            Ingested packet with ID
        """
        packet_id = str(uuid4())

        packet = {
            "packet_id": packet_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        }

        # Check for large content that needs blob offload
        content = data.get("content", "")
        if isinstance(content, str) and len(content) > self.blob_threshold_kb * 1024:
            blob_id = await self.store_blob(content)
            packet["blob_id"] = blob_id
            packet["content"] = f"[blob:{blob_id}]"

        self.packets[packet_id] = packet

        # Add to vector index
        self.vectors.append(
            {
                "id": packet_id,
                "content": data.get("content", ""),
                "metadata": data,
            }
        )

        return packet

    async def retrieve(self, packet_id: str) -> dict[str, Any] | None:
        """
        Retrieve a packet by ID.

        Args:
            packet_id: Packet ID

        Returns:
            Packet data or None
        """
        packet = self.packets.get(packet_id)

        if packet and "blob_id" in packet:
            # Retrieve blob content
            blob_content = await self.retrieve_blob(packet["blob_id"])
            if blob_content:
                packet = packet.copy()
                packet["content"] = blob_content.decode("utf-8")

        return packet

    @must_stay_async("callers use await")
    async def run_pruning(self) -> dict[str, Any]:
        """
        Run vector index pruning.

        Removes oldest vectors when exceeding max_vectors limit.

        Returns:
            Pruning statistics
        """
        original_count = len(self.vectors)

        if original_count > self.max_vectors:
            # Keep only the most recent vectors
            self.vectors = self.vectors[-self.max_vectors :]

        return {
            "original_vectors": original_count,
            "active_vectors": len(self.vectors),
            "pruned": original_count - len(self.vectors),
        }

    @must_stay_async("callers use await")
    async def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search vectors by query.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of matching vectors
        """
        # Simple substring matching for mock
        results = []
        for vec in self.vectors:
            content = vec.get("content", "")
            if query.lower() in content.lower():
                results.append(vec)
                if len(results) >= top_k:
                    break

        return results

    @must_stay_async("callers use await")
    async def save_checkpoint(self, data: dict[str, Any]) -> str:
        """
        Save a checkpoint.

        Args:
            data: Checkpoint data

        Returns:
            Checkpoint ID
        """
        checkpoint_id = str(uuid4())
        self.checkpoints[checkpoint_id] = {
            "id": checkpoint_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        }
        return checkpoint_id

    @must_stay_async("callers use await")
    async def load_checkpoint(self, thread_id: str) -> dict[str, Any] | None:
        """
        Load the latest checkpoint for a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Checkpoint data or None
        """
        # Return the most recent checkpoint
        if self.checkpoints:
            return list(self.checkpoints.values())[-1]
        return None

    def fork(self) -> MockMemoryAdapter:
        """
        Create a fork of this adapter.

        Returns:
            New adapter with shared state
        """
        forked = MockMemoryAdapter(
            max_vectors=self.max_vectors,
            blob_threshold_kb=self.blob_threshold_kb,
        )
        forked.packets = self.packets.copy()
        forked.vectors = self.vectors.copy()
        forked.checkpoints = self.checkpoints.copy()
        forked.blob_store = self.blob_store
        return forked

    def get_stats(self) -> dict[str, Any]:
        """Get adapter statistics."""
        return {
            "packet_count": len(self.packets),
            "vector_count": len(self.vectors),
            "blob_count": len(self.blob_store.blobs),
            "checkpoint_count": len(self.checkpoints),
        }


class MockPostgresCursor:
    """
    Mock PostgreSQL cursor for testing.

    Simulates database queries without requiring an actual database.
    """

    def __init__(self):
        self._results: list[tuple] = []
        self._index_definitions = {
            "memory_vectors_idx": "CREATE INDEX memory_vectors_idx ON memory_vectors USING ivfflat (embedding vector_cosine_ops)",
        }

    def execute(self, query: str, params: tuple = ()) -> None:
        """
        Execute a query.

        Args:
            query: SQL query
            params: Query parameters
        """
        # Handle index query
        if "pg_indexes" in query.lower() and "memory_vectors_idx" in query:
            self._results = [(self._index_definitions.get("memory_vectors_idx", ""),)]
        else:
            self._results = []

    def fetchone(self) -> tuple | None:
        """Fetch one result."""
        if self._results:
            return self._results[0]
        return None

    def fetchall(self) -> list[tuple]:
        """Fetch all results."""
        return self._results

    def fetchmany(self, size: int = 1) -> list[tuple]:
        """Fetch many results."""
        return self._results[:size]

    def close(self) -> None:
        """Close cursor."""
        pass


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter-pattern",
        "async",
        "dataclass",
        "mocking",
        "operations",
        "security",
        "testing",
        "tests",
    ],
    "keywords": [
        "adapter",
        "blob",
        "checkpoint",
        "close",
        "cursor",
        "delete",
        "execute",
        "fetchall",
    ],
    "business_value": "Provides memory mocks components including MockBlobStore, MockMemoryAdapter, MockPostgresCursor",
    "last_modified": "2026-01-07T13:35:58Z",
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
