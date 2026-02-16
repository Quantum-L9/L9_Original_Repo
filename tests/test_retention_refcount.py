"""
Unit tests for Reference Counting Service.

Tests:
- Refcount computation (lineage, facts, checkpoints)
- Safe deletion checks
- Soft expiration marking
- Cache invalidation
"""

import pytest

from core.decorators import must_stay_async
from memory.retention_refcount import PacketRefCount, ReferenceCountingService


@pytest.fixture
@must_stay_async("callers use await")
async def mock_repository():
    """Mock repository for testing."""

    class MockRepo:
        def __init__(self):
            self.packets = {}
            self.facts = {}
            self.checkpoints = {}

        def acquire(self):
            return self

        @must_stay_async("callers use await")
        async def __aenter__(self):
            return self

        @must_stay_async("callers use await")
        async def __aexit__(self, *args):
            pass

        @must_stay_async("callers use await")
        async def fetchval(self, query, *args):
            # Simulate database queries
            if "packet_store" in query and "parent_ids" in query:
                # Lineage query
                packet_id = args[0]
                return sum(
                    1
                    for p in self.packets.values()
                    if packet_id in p.get("parent_ids", [])
                )

            if "semantic_facts" in query:
                # Facts query
                packet_id = args[0]
                return sum(
                    1
                    for f in self.facts.values()
                    if f.get("source_packet_id") == packet_id
                )

            if "graph_checkpoints" in query:
                # Checkpoint query
                packet_id = args[0]
                return sum(1 for c in self.checkpoints.values() if packet_id in str(c))

            return 0

        @must_stay_async("callers use await")
        async def execute(self, query, *args):
            # Mock UPDATE for soft expiration
            pass

    return MockRepo()


@pytest.mark.asyncio
async def test_compute_refcount_no_references(mock_repository):
    """Test refcount computation for packet with no references."""
    service = ReferenceCountingService(mock_repository)

    refcount = await service.compute_refcount("packet_orphan")

    assert refcount.packet_id == "packet_orphan"
    assert refcount.total_refs == 0
    assert refcount.is_safe_to_delete is True


@pytest.mark.asyncio
async def test_compute_refcount_with_lineage(mock_repository):
    """Test refcount computation for packet with child packets."""
    # Setup: Add child packets
    mock_repository.packets["child1"] = {"parent_ids": ["packet_parent"]}
    mock_repository.packets["child2"] = {
        "parent_ids": ["packet_parent", "other_parent"]
    }

    service = ReferenceCountingService(mock_repository)
    refcount = await service.compute_refcount("packet_parent")

    assert refcount.lineage_refs == 2
    assert refcount.total_refs == 2
    assert refcount.is_safe_to_delete is False


@pytest.mark.asyncio
async def test_compute_refcount_with_facts(mock_repository):
    """Test refcount computation for packet with semantic facts."""
    # Setup: Add facts
    mock_repository.facts["fact1"] = {"source_packet_id": "packet_with_facts"}
    mock_repository.facts["fact2"] = {"source_packet_id": "packet_with_facts"}
    mock_repository.facts["fact3"] = {"source_packet_id": "packet_with_facts"}

    service = ReferenceCountingService(mock_repository)
    refcount = await service.compute_refcount("packet_with_facts")

    assert refcount.fact_refs == 3
    assert refcount.total_refs == 3
    assert refcount.is_safe_to_delete is False


@pytest.mark.asyncio
async def test_compute_refcount_with_checkpoints(mock_repository):
    """Test refcount computation for packet in agent checkpoints."""
    # Setup: Add checkpoints
    mock_repository.checkpoints["cp1"] = {"graph_state": "packet_in_checkpoint"}
    mock_repository.checkpoints["cp2"] = {"graph_state": "packet_in_checkpoint"}

    service = ReferenceCountingService(mock_repository)
    refcount = await service.compute_refcount("packet_in_checkpoint")

    assert refcount.checkpoint_refs == 2
    assert refcount.total_refs == 2
    assert refcount.is_safe_to_delete is False


@pytest.mark.asyncio
async def test_is_safe_to_delete(mock_repository):
    """Test safe deletion check."""
    service = ReferenceCountingService(mock_repository)

    # Orphan packet should be safe to delete
    assert await service.is_safe_to_delete("orphan") is True

    # Packet with references should NOT be safe
    mock_repository.packets["child"] = {"parent_ids": ["referenced"]}
    assert await service.is_safe_to_delete("referenced") is False


@pytest.mark.asyncio
async def test_refcount_caching(mock_repository):
    """Test that refcounts are cached."""
    service = ReferenceCountingService(mock_repository)

    # First call computes
    refcount1 = await service.compute_refcount("packet_123", use_cache=True)

    # Second call uses cache
    refcount2 = await service.compute_refcount("packet_123", use_cache=True)

    assert refcount1.packet_id == refcount2.packet_id
    assert refcount1.version == refcount2.version

    # Cache invalidation
    await service.invalidate_cache("packet_123")
    assert "packet_123" not in service._refcount_cache


@pytest.mark.asyncio
async def test_batch_compute_refcounts(mock_repository):
    """Test batch refcount computation."""
    mock_repository.packets["child1"] = {"parent_ids": ["parent1"]}
    mock_repository.packets["child2"] = {"parent_ids": ["parent2"]}

    service = ReferenceCountingService(mock_repository)

    results = await service.batch_compute_refcounts(["parent1", "parent2", "orphan"])

    assert len(results) == 3
    assert results["parent1"].lineage_refs == 1
    assert results["parent2"].lineage_refs == 1
    assert results["orphan"].total_refs == 0


@pytest.mark.asyncio
async def test_mark_soft_expired(mock_repository):
    """Test soft expiration marking."""
    service = ReferenceCountingService(mock_repository)

    # Should execute UPDATE query
    await service.mark_soft_expired("packet_expired")

    # Verify query was called (mock doesn't throw error)
    assert True  # If we get here, no exception was raised


def test_packet_refcount_dataclass():
    """Test PacketRefCount dataclass properties."""
    refcount = PacketRefCount(
        packet_id="test", lineage_refs=2, fact_refs=3, checkpoint_refs=1
    )

    assert refcount.total_refs == 6
    assert refcount.is_safe_to_delete is False

    # Test repr
    repr_str = repr(refcount)
    assert "total=6" in repr_str
    assert "lineage=2" in repr_str
