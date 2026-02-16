"""
Extraction Pipeline Tests
==========================

Tests to verify that extraction pipelines (extract_insights_node, store_insights_node)
execute automatically on packet ingestion and create knowledge facts.

NOTE: Integration tests requiring live PostgreSQL.
"""

import asyncio
import os

import pytest

from core.decorators import must_stay_async

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="Requires TEST_DATABASE_URL (integration test — set to a reachable PostgreSQL URL)",
)

from core.schemas import PacketEnvelopeIn
from memory.substrate_service import MemorySubstrateService, close_service, init_service


@pytest.fixture
async def memory_substrate_service():
    """Provide a memory substrate service for testing."""
    service = await init_service(TEST_DB_URL)
    yield service
    await close_service()


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_extraction_pipeline_creates_facts(
    memory_substrate_service: MemorySubstrateService,
):
    """
    Contract: When a packet is ingested, extract_insights_node and store_insights_node
    execute automatically and create knowledge facts in knowledge_facts table.
    """
    # Create a packet with structured payload that should generate facts
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={
            "subject": "TestComponent",
            "status": "active",
            "version": "1.0.0",
            "description": "Test component for extraction pipeline verification",
        },
        agent_id="test_agent",
    )

    # Ingest the packet
    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok", f"Packet ingestion failed: {result.error_message}"
    assert result.packet_id is not None

    # Wait a moment for async DAG processing
    await asyncio.sleep(0.5)

    # Verify knowledge facts were created
    facts = await memory_substrate_service.get_facts_by_subject(
        subject="TestComponent",
        limit=10,
    )

    # Should have at least one fact (status, version, or description)
    assert len(facts) > 0, (
        "Extraction pipeline should create at least one knowledge fact"
    )

    # Verify facts contain expected predicates
    predicates = [f["predicate"] for f in facts]
    assert (
        "status" in predicates or "version" in predicates or "description" in predicates
    ), f"Expected facts with status/version/description predicates, got: {predicates}"

    # Verify facts reference the source packet
    for fact in facts:
        assert fact["source_packet"] == str(result.packet_id), (
            f"Fact should reference source packet {result.packet_id}, got {fact.get('source_packet')}"
        )


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_extraction_pipeline_with_reasoning_block(
    memory_substrate_service: MemorySubstrateService,
):
    """
    Contract: Packets with reasoning blocks trigger insight extraction.
    """
    packet_in = PacketEnvelopeIn(
        packet_type="reasoning",
        payload={
            "text": "Decision made to use approach A",
            "conclusion": "Approach A selected",
        },
        metadata={
            "reasoning_block": {
                "decision_tokens": ["store_packet:true", "route_to:agent"],
                "confidence_scores": {"routing": 0.85},
            }
        },
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"

    # Wait for DAG processing
    await asyncio.sleep(0.5)

    # Check that facts were created from payload
    all_facts = await memory_substrate_service.get_facts_by_subject(
        subject=None,  # Get all facts
        limit=100,
    )

    # Find facts from this packet
    packet_facts = [f for f in all_facts if f["source_packet"] == str(result.packet_id)]
    assert len(packet_facts) > 0, (
        "Should have created facts from packet with reasoning block"
    )


@pytest.mark.asyncio
async def test_extraction_pipeline_handles_empty_payload(
    memory_substrate_service: MemorySubstrateService,
):
    """
    Contract: Packets with minimal payload don't cause extraction errors.
    """
    packet_in = PacketEnvelopeIn(
        packet_type="minimal",
        payload={},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok", "Empty payload should not cause ingestion failure"

    # Wait for DAG processing
    await asyncio.sleep(0.5)

    # Extraction should complete without errors (may create 0 facts, which is OK)
    # Just verify the packet was stored
    envelope = await memory_substrate_service.get_packet(result.packet_id)
    assert envelope is not None, "Packet should be retrievable even with empty payload"
