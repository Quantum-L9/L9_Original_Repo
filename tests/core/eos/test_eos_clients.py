"""
Tests for EOS Clients — Hypergraph & Ledger
============================================

Tests for EOSHypergraphClient and EOSLedgerWriter.

Version: 1.0.0
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.eos.hypergraph_client import EOSHypergraphClient
from core.eos.ledger_writer import EOSLedgerWriter
from core.eos.schemas import LedgerEntry

# =============================================================================
# Mock Neo4j Client
# =============================================================================


class MockNeo4jClient:
    """Mock Neo4j client for testing."""

    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self.read_results: list[list[dict[str, Any]]] = []
        self.write_results: list[list[dict[str, Any]]] = []
        self._read_index = 0
        self._write_index = 0
        self.should_fail: bool = False

    def set_read_results(self, results: list[list[dict[str, Any]]]) -> None:
        """Set sequence of read results."""
        self.read_results = results
        self._read_index = 0

    def set_write_results(self, results: list[list[dict[str, Any]]]) -> None:
        """Set sequence of write results."""
        self.write_results = results
        self._write_index = 0

    async def execute_read(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Execute a read query."""
        self.queries.append({"type": "read", "query": query, "params": params})

        if self.should_fail:
            raise RuntimeError("Neo4j read failed")

        if self._read_index < len(self.read_results):
            result = self.read_results[self._read_index]
            self._read_index += 1
            return result
        return []

    async def execute_write(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Execute a write query."""
        self.queries.append({"type": "write", "query": query, "params": params})

        if self.should_fail:
            raise RuntimeError("Neo4j write failed")

        if self._write_index < len(self.write_results):
            result = self.write_results[self._write_index]
            self._write_index += 1
            return result
        return [{"id": str(uuid4())}]


# =============================================================================
# Mock Substrate Service
# =============================================================================


class MockSubstrateService:
    """Mock substrate service for testing."""

    def __init__(self) -> None:
        self.packets: list[dict[str, Any]] = []
        self.should_fail: bool = False

    async def ingest_packet(self, packet: dict[str, Any]) -> str:
        """Ingest a packet."""
        if self.should_fail:
            raise RuntimeError("Substrate ingest failed")

        packet_id = str(uuid4())
        self.packets.append({"id": packet_id, **packet})
        return packet_id

    async def search_packets_by_type(
        self,
        packet_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search packets by type."""
        return [p for p in self.packets if p.get("packet_type") == packet_type][:limit]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j() -> MockNeo4jClient:
    """Create mock Neo4j client."""
    return MockNeo4jClient()


@pytest.fixture
def mock_substrate() -> MockSubstrateService:
    """Create mock substrate service."""
    return MockSubstrateService()


@pytest.fixture
def hypergraph_client(mock_neo4j: MockNeo4jClient) -> EOSHypergraphClient:
    """Create hypergraph client with mock Neo4j."""
    return EOSHypergraphClient(neo4j_client=mock_neo4j)


@pytest.fixture
def ledger_writer(mock_substrate: MockSubstrateService) -> EOSLedgerWriter:
    """Create ledger writer with mock substrate."""
    return EOSLedgerWriter(substrate_service=mock_substrate)


# =============================================================================
# EOSHypergraphClient Tests
# =============================================================================


class TestEOSHypergraphClient:
    """Tests for EOSHypergraphClient."""

    def test_init_with_neo4j(self, mock_neo4j: MockNeo4jClient) -> None:
        """Test initialization with Neo4j client."""
        client = EOSHypergraphClient(neo4j_client=mock_neo4j)
        assert client.available is True

    def test_init_without_neo4j(self) -> None:
        """Test initialization without Neo4j client."""
        client = EOSHypergraphClient(neo4j_client=None)
        assert client.available is False

    @pytest.mark.asyncio
    async def test_check_violations_no_violations(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test check_violations with no violations found."""
        # Set up mock to return no prohibitions, one capability
        mock_neo4j.set_read_results(
            [
                [],  # No prohibitions
                [
                    {"capability": "tool_call", "scope": "all", "risk_class": "low"}
                ],  # Has capability
                [],  # No obligations
            ]
        )

        result = await hypergraph_client.check_violations(
            action_type="tool_call",
            agent_id="agent-001",
        )

        assert result["checked"] is True
        assert len(result["violations"]) == 0
        assert len(result["satisfied"]) == 1

    @pytest.mark.asyncio
    async def test_check_violations_with_prohibition(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test check_violations when prohibition is found."""
        mock_neo4j.set_read_results(
            [
                [
                    {
                        "prohibition": "no_deploy",
                        "description": "Deployments blocked",
                        "severity": "high",
                    }
                ],
                [{"capability": "deploy", "scope": "all", "risk_class": "high"}],
                [],
            ]
        )

        result = await hypergraph_client.check_violations(
            action_type="deploy",
            agent_id="agent-001",
        )

        assert result["checked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "prohibition"
        assert result["violations"][0]["name"] == "no_deploy"

    @pytest.mark.asyncio
    async def test_check_violations_missing_capability(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test check_violations when agent lacks capability."""
        mock_neo4j.set_read_results(
            [
                [],  # No prohibitions
                [],  # No capabilities
                [],  # No obligations
            ]
        )

        result = await hypergraph_client.check_violations(
            action_type="deploy",
            agent_id="agent-001",
        )

        assert result["checked"] is True
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "missing_capability"

    @pytest.mark.asyncio
    async def test_check_violations_unavailable(self) -> None:
        """Test check_violations when client unavailable."""
        client = EOSHypergraphClient(neo4j_client=None)

        result = await client.check_violations(
            action_type="tool_call",
            agent_id="agent-001",
        )

        assert result["checked"] is False
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_check_violations_error_handling(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test check_violations handles Neo4j errors gracefully."""
        mock_neo4j.should_fail = True

        result = await hypergraph_client.check_violations(
            action_type="tool_call",
            agent_id="agent-001",
        )

        assert result["checked"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_record_verdict(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test recording a verdict to hypergraph."""
        mock_neo4j.set_write_results([[{"id": "verdict-001"}]])

        result = await hypergraph_client.record_verdict(
            verdict_id="verdict-001",
            action_id="action-001",
            decision="allow",
            agent_id="agent-001",
            justification=["capability_verified"],
        )

        assert result is True
        assert len(mock_neo4j.queries) == 1
        assert mock_neo4j.queries[0]["type"] == "write"

    @pytest.mark.asyncio
    async def test_get_agent_capabilities(
        self,
        hypergraph_client: EOSHypergraphClient,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test getting agent capabilities."""
        mock_neo4j.set_read_results(
            [
                [
                    {
                        "name": "tool_call",
                        "action_type": "tool_call",
                        "scope": "all",
                        "risk_class": "low",
                    },
                    {
                        "name": "code_diff",
                        "action_type": "code_diff",
                        "scope": "workspace",
                        "risk_class": "medium",
                    },
                ]
            ]
        )

        capabilities = await hypergraph_client.get_agent_capabilities("agent-001")

        assert len(capabilities) == 2
        assert capabilities[0]["name"] == "tool_call"


# =============================================================================
# EOSLedgerWriter Tests
# =============================================================================


class TestEOSLedgerWriter:
    """Tests for EOSLedgerWriter."""

    def test_init_with_substrate(self, mock_substrate: MockSubstrateService) -> None:
        """Test initialization with substrate service."""
        writer = EOSLedgerWriter(substrate_service=mock_substrate)
        assert writer.available is True

    def test_init_without_substrate(self) -> None:
        """Test initialization without substrate service."""
        writer = EOSLedgerWriter(substrate_service=None)
        assert writer.available is False

    @pytest.mark.asyncio
    async def test_write_ledger_entry(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test writing a ledger entry."""
        entry = LedgerEntry(
            entry_id=str(uuid4()),
            hash="",
            signer="accountability_engine",
            timestamp=datetime.now(timezone.utc),
            action_ref="action-001",
            verdict_ref="verdict-001",
            payload={"decision": "allow", "risk_class": "low"},
        )

        result = await ledger_writer.write(entry)

        assert result is not None  # Hash returned
        assert len(result) == 64  # SHA-256 hex
        assert len(mock_substrate.packets) == 1
        assert mock_substrate.packets[0]["packet_type"] == "eos.ledger.entry"

    @pytest.mark.asyncio
    async def test_write_verdict_entry(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test writing a verdict entry."""
        result = await ledger_writer.write_verdict_entry(
            verdict_id="verdict-001",
            action_id="action-001",
            decision="allow",
            agent_id="agent-001",
            risk_class="low",
            justification=["capability_verified"],
        )

        assert result is not None
        assert len(mock_substrate.packets) == 1

        packet = mock_substrate.packets[0]
        payload = packet["payload"]["ledger_entry"]["payload"]
        assert payload["event_type"] == "verdict_issued"
        assert payload["decision"] == "allow"

    @pytest.mark.asyncio
    async def test_write_action_entry(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test writing an action entry."""
        result = await ledger_writer.write_action_entry(
            action_id="action-001",
            action_type="tool_call",
            agent_id="agent-001",
            environment="dev",
            risk_class="low",
            status="completed",
        )

        assert result is not None
        assert len(mock_substrate.packets) == 1

        packet = mock_substrate.packets[0]
        payload = packet["payload"]["ledger_entry"]["payload"]
        assert payload["event_type"] == "action_completed"

    @pytest.mark.asyncio
    async def test_write_anomaly_entry(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test writing an anomaly entry."""
        result = await ledger_writer.write_anomaly_entry(
            source_id="tensorglobe_adapter",
            anomaly_type="confidence_collapse",
            anomaly_score=0.95,
            severity="high",
            action_taken="provider_suspended",
            context={"threshold": 0.85},
        )

        assert result is not None
        assert len(mock_substrate.packets) == 1

        packet = mock_substrate.packets[0]
        payload = packet["payload"]["ledger_entry"]["payload"]
        assert payload["event_type"] == "anomaly_detected"
        assert payload["anomaly_score"] == 0.95

    @pytest.mark.asyncio
    async def test_write_unavailable(self) -> None:
        """Test write when substrate unavailable."""
        writer = EOSLedgerWriter(substrate_service=None)

        entry = LedgerEntry(
            entry_id=str(uuid4()),
            hash="",
            signer="test",
            timestamp=datetime.now(timezone.utc),
            action_ref="action-001",
            verdict_ref=None,
            payload={},
        )

        result = await writer.write(entry)
        assert result is None

    @pytest.mark.asyncio
    async def test_write_error_handling(
        self,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test write handles substrate errors gracefully."""
        mock_substrate.should_fail = True
        writer = EOSLedgerWriter(substrate_service=mock_substrate)

        entry = LedgerEntry(
            entry_id=str(uuid4()),
            hash="",
            signer="test",
            timestamp=datetime.now(timezone.utc),
            action_ref="action-001",
            verdict_ref=None,
            payload={},
        )

        result = await writer.write(entry)
        assert result is None

    @pytest.mark.asyncio
    async def test_hash_chain_linking(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test that entries are chain-linked via previous_hash."""
        # Write first entry
        await ledger_writer.write_action_entry(
            action_id="action-001",
            action_type="tool_call",
            agent_id="agent-001",
            environment="dev",
            risk_class="low",
            status="submitted",
        )

        first_hash = mock_substrate.packets[0]["payload"]["hash"]

        # Write second entry
        await ledger_writer.write_action_entry(
            action_id="action-002",
            action_type="tool_call",
            agent_id="agent-001",
            environment="dev",
            risk_class="low",
            status="completed",
        )

        second_previous = mock_substrate.packets[1]["payload"]["previous_hash"]

        # Second entry should reference first entry's hash
        assert second_previous == first_hash

    @pytest.mark.asyncio
    async def test_get_recent_entries(
        self,
        ledger_writer: EOSLedgerWriter,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test retrieving recent ledger entries."""
        # Write some entries
        await ledger_writer.write_verdict_entry(
            verdict_id="v1",
            action_id="a1",
            decision="allow",
            agent_id="agent-001",
            risk_class="low",
        )

        entries = await ledger_writer.get_recent_entries(limit=10)
        assert len(entries) == 1


# =============================================================================
# Integration Tests (AccountabilityEngine with Real Clients)
# =============================================================================


class TestAccountabilityEngineIntegration:
    """Integration tests for AccountabilityEngine with real clients."""

    @pytest.mark.asyncio
    async def test_engine_with_hypergraph_client(
        self,
        mock_neo4j: MockNeo4jClient,
    ) -> None:
        """Test AccountabilityEngine uses hypergraph client."""
        from core.eos import (
            AccountabilityEngine,
            ActionEnvelope,
            ActionType,
            Environment,
            RiskClass,
        )

        hypergraph = EOSHypergraphClient(neo4j_client=mock_neo4j)
        engine = AccountabilityEngine(hypergraph_client=hypergraph)

        # Set up mock to return capabilities
        mock_neo4j.set_read_results(
            [
                [],  # No prohibitions
                [{"capability": "tool_call", "scope": "all", "risk_class": "low"}],
                [],  # No obligations
            ]
        )

        action = ActionEnvelope(
            agent_id="agent-001",
            action_type=ActionType.TOOL_CALL,
            payload_ref="test://payload",
            claimed_authority="L",
            signature="test_sig",
            signing_key_id="key-001",
            environment=Environment.DEV,
            risk_class=RiskClass.LOW,
        )

        _verdict, _violations = await engine.evaluate_action(action)

        # Hypergraph was queried
        assert len(mock_neo4j.queries) >= 1

    @pytest.mark.asyncio
    async def test_engine_with_ledger_writer(
        self,
        mock_substrate: MockSubstrateService,
    ) -> None:
        """Test AccountabilityEngine uses ledger writer."""
        from core.eos import (
            AccountabilityEngine,
            ActionEnvelope,
            ActionType,
            Environment,
            RiskClass,
        )

        ledger = EOSLedgerWriter(substrate_service=mock_substrate)
        engine = AccountabilityEngine(ledger_writer=ledger)

        action = ActionEnvelope(
            agent_id="agent-001",
            action_type=ActionType.TOOL_CALL,
            payload_ref="test://payload",
            claimed_authority="L",
            signature="test_sig",
            signing_key_id="key-001",
            environment=Environment.DEV,
            risk_class=RiskClass.MEDIUM,  # Medium+ triggers ledger write
        )

        _verdict, _violations = await engine.evaluate_action(action)

        # Ledger was written
        assert len(mock_substrate.packets) >= 1


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "MockNeo4jClient",
    "MockSubstrateService",
]
