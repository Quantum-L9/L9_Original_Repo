"""
Reasoning Replay Pipeline Tests
================================

Tests for memory.reasoning_replay.ReasoningReplayPipeline.
Verifies decision chain reconstruction and explainability.

NOTE: Integration tests requiring live PostgreSQL.
"""

import os

import pytest

from core.decorators import must_stay_async

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="Requires TEST_DATABASE_URL (integration test — set to a reachable PostgreSQL URL)",
)

from core.schemas import PacketEnvelopeIn
from memory.reasoning_replay import ReasoningReplayPipeline
from memory.substrate_service import MemorySubstrateService, close_service, init_service


@pytest.fixture
async def memory_substrate_service():
    """Provide a memory substrate service for testing."""
    service = await init_service(TEST_DB_URL)
    yield service
    await close_service()


@pytest.fixture
def reasoning_replay_pipeline(memory_substrate_service):
    """Provide a ReasoningReplayPipeline instance."""
    return ReasoningReplayPipeline(repository=memory_substrate_service._repository)


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_reasoning_replay_initialization(reasoning_replay_pipeline):
    """Test ReasoningReplayPipeline can be instantiated."""
    assert reasoning_replay_pipeline is not None
    assert reasoning_replay_pipeline._repository is not None


@pytest.mark.asyncio
async def test_reconstruct_chain_single_packet(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test reconstruct_chain with a single packet (no parents)."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={"action": "test"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Reconstruct chain
    chain = await reasoning_replay_pipeline.reconstruct_chain(packet_id)

    assert chain is not None
    assert chain.start_packet_id == packet_id
    assert len(chain.packets) == 1
    assert chain.packets[0]["packet_id"] == str(packet_id)


@pytest.mark.asyncio
async def test_get_decision_ancestors_no_parents(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test get_decision_ancestors with packet that has no parents."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={"action": "test"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Get ancestors
    ancestors = await reasoning_replay_pipeline.get_decision_ancestors(packet_id)

    # Should return empty list (no parents)
    assert ancestors == []


@pytest.mark.asyncio
async def test_explain_decision_json_format(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test explain_decision with json format."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="decision",
        payload={"decision": "approve", "reason": "test"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Explain decision
    explanation = await reasoning_replay_pipeline.explain_decision(
        packet_id, format="json"
    )

    assert explanation is not None
    assert "chain_id" in explanation
    assert "start_packet_id" in explanation
    assert "packets" in explanation
    import json

    # Should be valid JSON
    parsed = json.loads(explanation)
    assert parsed["start_packet_id"] == str(packet_id)


@pytest.mark.asyncio
async def test_explain_decision_narrative_format(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test explain_decision with narrative format."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="decision",
        payload={"decision": "approve"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Explain decision
    explanation = await reasoning_replay_pipeline.explain_decision(
        packet_id, format="narrative"
    )

    assert explanation is not None
    assert isinstance(explanation, str)
    assert "Decision Chain" in explanation
    assert str(packet_id) in explanation


@pytest.mark.asyncio
async def test_explain_decision_graph_viz_format(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test explain_decision with graph_viz format."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="decision",
        payload={"decision": "approve"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Explain decision
    explanation = await reasoning_replay_pipeline.explain_decision(
        packet_id, format="graph_viz"
    )

    assert explanation is not None
    assert isinstance(explanation, str)
    assert "digraph" in explanation
    assert "DecisionChain" in explanation


@pytest.mark.asyncio
async def test_explain_decision_mermaid_format(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test explain_decision with mermaid format."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="decision",
        payload={"decision": "approve"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Explain decision
    explanation = await reasoning_replay_pipeline.explain_decision(
        packet_id, format="mermaid"
    )

    assert explanation is not None
    assert isinstance(explanation, str)
    assert "graph TD" in explanation


@pytest.mark.asyncio
async def test_explain_decision_invalid_format(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test explain_decision raises error for invalid format."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="decision",
        payload={"decision": "approve"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Explain decision with invalid format
    with pytest.raises(ValueError, match="Unsupported format"):
        await reasoning_replay_pipeline.explain_decision(packet_id, format="invalid")


@pytest.mark.asyncio
async def test_verify_lineage_integrity_valid(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test verify_lineage_integrity with valid packet."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={"action": "test"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Verify integrity
    is_valid = await reasoning_replay_pipeline.verify_lineage_integrity(packet_id)

    # Should be valid (no parents, no cycles)
    assert is_valid is True


@pytest.mark.asyncio
async def test_detect_orphaned_packets_no_orphans(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test detect_orphaned_packets returns empty list when no orphans exist."""
    # Create a valid packet (no parent references)
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={"action": "test"},
        agent_id="test_agent_orphan_check",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"

    # Should return empty list (no orphaned references)
    orphaned = await reasoning_replay_pipeline.detect_orphaned_packets(
        "test_agent_orphan_check"
    )

    assert isinstance(orphaned, list)
    # Packet has no parent_ids, so should not be detected as orphaned
    assert result.packet_id not in orphaned


@pytest.mark.asyncio
async def test_detect_orphaned_packets_returns_list(
    reasoning_replay_pipeline,
):
    """Test detect_orphaned_packets returns list even for non-existent agent."""
    orphaned = await reasoning_replay_pipeline.detect_orphaned_packets(
        "nonexistent_agent_12345"
    )

    assert isinstance(orphaned, list)
    assert len(orphaned) == 0


@pytest.mark.asyncio
async def test_repair_broken_lineage(
    reasoning_replay_pipeline,
    memory_substrate_service: MemorySubstrateService,
):
    """Test repair_broken_lineage with valid packet."""
    # Create a packet
    packet_in = PacketEnvelopeIn(
        packet_type="test_event",
        payload={"action": "test"},
        agent_id="test_agent",
    )

    result = await memory_substrate_service.write_packet(packet_in)
    assert result.status == "ok"
    packet_id = result.packet_id

    # Repair lineage (should succeed for valid packet)
    repaired = await reasoning_replay_pipeline.repair_broken_lineage(packet_id)

    # Should return True for valid packet
    assert repaired is True
