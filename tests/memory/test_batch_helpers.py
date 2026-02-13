"""
Tests for batch query helpers

These tests verify that batch query helpers prevent N+1 patterns
and correctly fetch related data.

NOTE: These are integration tests that require a live PostgreSQL database.
"""

import os
from datetime import UTC, datetime, timezone
from uuid import uuid4

import pytest

from core.decorators import must_stay_async
from memory.substrate_repository_batch_helpers import BatchQueryHelpers

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="Requires TEST_DATABASE_URL (integration test — set to a reachable PostgreSQL URL)",
)


@pytest.fixture
async def substrate_repo():
    """Provide a SubstrateRepository connected to the test database.

    Skips if TEST_DATABASE_URL is not set.
    """
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    from memory.substrate_repository import SubstrateRepository

    repo = SubstrateRepository(TEST_DB_URL)
    await repo.initialize()
    yield repo
    await repo.close()


@pytest.fixture
@must_stay_async("callers use await")
async def batch_helpers(substrate_repo):
    """Provide BatchQueryHelpers instance"""
    return BatchQueryHelpers(substrate_repo)


@pytest.fixture
async def sample_packets(substrate_repo):
    """Create sample packets for testing"""
    tenant_id = "test-tenant"
    packet_ids = [uuid4() for _ in range(5)]

    async with substrate_repo.acquire() as conn:
        # Insert sample packets
        for packet_id in packet_ids:
            await conn.execute(
                """
                INSERT INTO packets (
                    packet_id, packet_type, envelope, timestamp,
                    tenant_id, tags
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                packet_id,
                "test",
                '{"test": true}',
                datetime.now(UTC),
                tenant_id,
                ["test"],
            )

    yield {"packet_ids": packet_ids, "tenant_id": tenant_id}

    # Cleanup
    async with substrate_repo.acquire() as conn:
        await conn.execute("DELETE FROM packets WHERE packet_id = ANY($1)", packet_ids)


@pytest.mark.asyncio
async def test_get_packets_with_metadata_batch(batch_helpers, sample_packets):
    """Test fetching packets with metadata in batch"""
    packet_ids = sample_packets["packet_ids"]
    tenant_id = sample_packets["tenant_id"]

    # Fetch packets with metadata
    packets = await batch_helpers.get_packets_with_metadata_batch(packet_ids, tenant_id)

    # Verify results
    assert len(packets) == len(packet_ids)
    for packet in packets:
        assert "packet_id" in packet
        assert "envelope" in packet
        assert packet["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_get_packets_with_children_batch(batch_helpers, substrate_repo):
    """Test fetching packets with children"""
    tenant_id = "test-tenant"
    parent_id = uuid4()
    child_ids = [uuid4() for _ in range(3)]

    async with substrate_repo.acquire() as conn:
        # Insert parent
        await conn.execute(
            """
            INSERT INTO packets (
                packet_id, packet_type, envelope, timestamp,
                tenant_id, parent_ids
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            parent_id,
            "parent",
            '{"type": "parent"}',
            datetime.now(UTC),
            tenant_id,
            [],
        )

        # Insert children
        for child_id in child_ids:
            await conn.execute(
                """
                INSERT INTO packets (
                    packet_id, packet_type, envelope, timestamp,
                    tenant_id, parent_ids
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                child_id,
                "child",
                '{"type": "child"}',
                datetime.now(UTC),
                tenant_id,
                [parent_id],
            )

    try:
        # Fetch parent with children
        children_by_parent = await batch_helpers.get_packets_with_children_batch(
            [parent_id], tenant_id
        )

        # Verify results
        assert parent_id in children_by_parent
        assert len(children_by_parent[parent_id]) == 3

        for child in children_by_parent[parent_id]:
            assert parent_id in child["parent_ids"]

    finally:
        # Cleanup
        async with substrate_repo.acquire() as conn:
            await conn.execute(
                "DELETE FROM packets WHERE packet_id = ANY($1)", [parent_id, *child_ids]
            )


@pytest.mark.asyncio
async def test_update_packets_status_batch(batch_helpers, sample_packets):
    """Test batch status update"""
    packet_ids = sample_packets["packet_ids"]
    tenant_id = sample_packets["tenant_id"]

    # Update status
    updated = await batch_helpers.update_packets_status_batch(
        packet_ids, "completed", tenant_id
    )

    # Verify update count
    assert updated == len(packet_ids)


@pytest.mark.asyncio
async def test_add_tags_batch(batch_helpers, sample_packets):
    """Test batch tag addition"""
    packet_ids = sample_packets["packet_ids"]
    tenant_id = sample_packets["tenant_id"]

    # Add tags
    updated = await batch_helpers.add_tags_batch(
        packet_ids, ["new_tag", "another_tag"], tenant_id
    )

    # Verify update count
    assert updated == len(packet_ids)


@pytest.mark.asyncio
async def test_remove_tags_batch(batch_helpers, sample_packets):
    """Test batch tag removal"""
    packet_ids = sample_packets["packet_ids"]
    tenant_id = sample_packets["tenant_id"]

    # Remove tags
    updated = await batch_helpers.remove_tags_batch(packet_ids, ["test"], tenant_id)

    # Verify update count
    assert updated == len(packet_ids)


@pytest.mark.asyncio
async def test_archive_packets_batch(batch_helpers, sample_packets):
    """Test batch archiving"""
    packet_ids = sample_packets["packet_ids"]
    tenant_id = sample_packets["tenant_id"]

    # Archive packets
    archived = await batch_helpers.archive_packets_batch(packet_ids, tenant_id)

    # Verify archive count
    assert archived == len(packet_ids)


@pytest.mark.asyncio
async def test_empty_input_handling(batch_helpers):
    """Test that empty inputs are handled gracefully"""
    # Empty packet_ids should return empty results
    packets = await batch_helpers.get_packets_with_metadata_batch([])
    assert packets == []

    children = await batch_helpers.get_packets_with_children_batch([])
    assert children == {}

    updated = await batch_helpers.update_packets_status_batch([], "test")
    assert updated == 0


@pytest.mark.asyncio
async def test_tenant_isolation(batch_helpers, substrate_repo):
    """Test that tenant filtering works correctly"""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    packet_a = uuid4()
    packet_b = uuid4()

    async with substrate_repo.acquire() as conn:
        # Insert packets for two tenants
        await conn.execute(
            """
            INSERT INTO packets (
                packet_id, packet_type, envelope, timestamp, tenant_id
            )
            VALUES ($1, $2, $3, $4, $5)
            """,
            packet_a,
            "test",
            "{}",
            datetime.now(UTC),
            tenant_a,
        )
        await conn.execute(
            """
            INSERT INTO packets (
                packet_id, packet_type, envelope, timestamp, tenant_id
            )
            VALUES ($1, $2, $3, $4, $5)
            """,
            packet_b,
            "test",
            "{}",
            datetime.now(UTC),
            tenant_b,
        )

    try:
        # Fetch with tenant_a filter
        packets = await batch_helpers.get_packets_with_metadata_batch(
            [packet_a, packet_b], tenant_a
        )

        # Should only return tenant_a's packet
        assert len(packets) == 1
        assert packets[0]["packet_id"] == packet_a
        assert packets[0]["tenant_id"] == tenant_a

    finally:
        # Cleanup
        async with substrate_repo.acquire() as conn:
            await conn.execute(
                "DELETE FROM packets WHERE packet_id = ANY($1)", [packet_a, packet_b]
            )
