"""
Integration tests for Phase 0 Hardening features.

Tests end-to-end workflows:
- Retention with refcount checks
- Policy evaluation with conflict resolution
- Parallel consolidation pipeline
- Cache invalidation hooks
"""

import asyncio
from datetime import UTC, datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_retention_with_refcount_integration(mock_substrate, mock_repository):
    """Test RetentionEngine uses ReferenceCountingService correctly."""
    from memory.retention_engine import RetentionEngine
    from memory.retention_refcount import ReferenceCountingService

    # Setup: Create packets with references
    await mock_substrate.writepacket(
        packetid="parent_packet",
        packettype="OBSERVATION",
        content={"text": "Parent"},
        ttl=timedelta(seconds=1),  # Expire immediately for test
    )

    await mock_substrate.writepacket(
        packetid="child_packet",
        packettype="OBSERVATION",
        content={"text": "Child"},
        parent_ids=["parent_packet"],
    )

    # Run retention cleanup
    retention = RetentionEngine(mock_repository)
    results = await retention.runcleanup(agent_id="test_agent")

    # Verify parent was NOT deleted (has child reference)
    assert results["soft_expired"] > 0
    assert results["deleted"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_governance_with_policy_conflicts(mock_governance_engine):
    """Test governance engine handles policy conflicts."""
    from core.governance.policy_engine import PolicyConflictResolver
    from core.governance.policy_models import (
        PolicyDecision,
        PolicyPriority,
        PolicyResult,
    )

    # Simulate conflicting policies
    policy_results = [
        PolicyResult(
            decision=PolicyDecision.ALLOW,
            priority=PolicyPriority.HIGH,
            reason="User is admin",
            policy_name="RolePolicy",
        ),
        PolicyResult(
            decision=PolicyDecision.DENY,
            priority=PolicyPriority.HIGH,
            reason="Resource locked",
            policy_name="LockPolicy",
        ),
    ]

    decision = PolicyConflictResolver.resolve(policy_results)

    # Should escalate due to conflict at same priority
    assert decision.final_decision == PolicyDecision.REQUIRE_ESCALATION
    assert decision.has_conflict is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_consolidation_pipeline(mock_substrate, mock_embedder):
    """Test parallel consolidation executes phases correctly."""
    from memory.consolidation.parallel_pipeline import ParallelConsolidationPipeline

    pipeline = ParallelConsolidationPipeline(mock_substrate, mock_embedder)

    # Register test phases
    async def phase1(agent_id, context):
        await asyncio.sleep(0.05)
        context["phase1_done"] = True
        return ["artifact1"]

    async def phase2(agent_id, context):
        assert context.get("phase1_done") is True  # Dependency check
        await asyncio.sleep(0.05)
        return ["artifact2"]

    pipeline.register_phase("phase1", phase1, dependencies=[])
    pipeline.register_phase("phase2", phase2, dependencies=["phase1"])

    # Run pipeline
    results = await pipeline.run_consolidation(agent_id="test_agent")

    # Verify both phases completed
    assert results["phase1"].success is True
    assert results["phase2"].success is True
    assert results["phase1"].artifacts_created == 1
    assert results["phase2"].artifacts_created == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_invalidation_on_write(mock_cache, mock_event_bus):
    """Test cache invalidation hook responds to substrate writes."""
    from memory_cache.invalidation_hook import (
        SubstrateWriteEvent,
        WorkingMemoryInvalidationHook,
    )

    hook = WorkingMemoryInvalidationHook(mock_cache, mock_event_bus)

    # Populate cache
    await mock_cache.redis.set("agent:test:working_memory", "cached_data")

    # Trigger substrate write event
    event = SubstrateWriteEvent(
        event_type="INSERT",
        packet_id="new_packet",
        agent_id="test",
        timestamp=datetime.now(tz=UTC),
        metadata={},
    )

    await hook.handle_event(event)

    # Verify cache was invalidated
    cached_value = await mock_cache.redis.get("agent:test:working_memory")
    assert cached_value is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_versioned_snapshot_optimistic_locking(mock_cache):
    """Test versioned snapshots detect write conflicts."""
    from memory_cache.versioned_snapshots import (
        OptimisticLockError,
        VersionedSnapshotService,
    )

    service = VersionedSnapshotService(mock_cache)

    # Thread A: Get snapshot
    snapshot_a = await service.get_snapshot("agent_test")
    snapshot_a.data["key"] = "value_a"

    # Thread B: Get same snapshot (same version)
    snapshot_b = await service.get_snapshot("agent_test")
    snapshot_b.data["key"] = "value_b"

    # Thread A commits first
    success_a = await service.commit_snapshot(snapshot_a)
    assert success_a is True

    # Thread B commit should fail (version changed)
    with pytest.raises(OptimisticLockError):
        await service.commit_snapshot(snapshot_b)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_memory_lifecycle(mock_substrate, mock_cache):
    """Test complete memory lifecycle with all Phase 0 features."""
    from memory.retention_engine import RetentionEngine
    from memory.retention_refcount import ReferenceCountingService
    from memory_cache.invalidation_hook import WorkingMemoryInvalidationHook

    # 1. Write packet to substrate
    packet_id = await mock_substrate.writepacket(
        packettype="OBSERVATION",
        content={"text": "Test memory"},
        ttl=timedelta(hours=1),
    )

    # 2. Cache working memory
    await mock_cache.redis.set("agent:test:working_memory", "cached")

    # 3. Create reference (child packet)
    await mock_substrate.writepacket(
        packettype="DERIVED", content={"text": "Child"}, parent_ids=[packet_id]
    )

    # 4. Attempt TTL cleanup
    retention = RetentionEngine(mock_substrate.repository)
    refcount_service = ReferenceCountingService(mock_substrate.repository)

    is_safe = await refcount_service.is_safe_to_delete(packet_id)
    assert is_safe is False  # Has child reference

    # 5. Verify soft expiration
    await refcount_service.mark_soft_expired(packet_id)

    # 6. Cache invalidation
    hook = WorkingMemoryInvalidationHook(mock_cache)
    await hook.handle_event(
        SubstrateWriteEvent(
            event_type="UPDATE",
            packet_id=packet_id,
            agent_id="test",
            timestamp=datetime.now(tz=UTC),
            metadata={},
        )
    )

    # Verify cache cleared
    cached = await mock_cache.redis.get("agent:test:working_memory")
    assert cached is None


# Pytest fixtures
@pytest.fixture
def mock_substrate():
    """Mock SubstrateService for testing."""

    class MockSubstrate:
        def __init__(self):
            self.packets = {}
            self.repository = None

        async def writepacket(self, **kwargs):
            packet_id = kwargs.get("packetid", f"pkt_{len(self.packets)}")
            self.packets[packet_id] = kwargs
            return packet_id

    return MockSubstrate()


@pytest.fixture
def mock_cache():
    """Mock Redis cache for testing."""

    class MockRedis:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def set(self, key, value):
            self.data[key] = value

        async def delete(self, *keys):
            for key in keys:
                self.data.pop(key, None)
            return len(keys)

        async def keys(self, pattern):
            import fnmatch

            return [k for k in self.data if fnmatch.fnmatch(k, pattern)]

    class MockCache:
        def __init__(self):
            self.redis = MockRedis()

    return MockCache()
