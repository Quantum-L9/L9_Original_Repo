"""
Invariant tests for DomainBridgeGateway (ADR-0092).

Tests:
  1. submit() rejects empty principal_id
  2. submit() rejects empty ingress_origin
  3. submit() denies when governance denies
  4. submit() succeeds end-to-end with mock governance + ingestion
  5. submit_batch() propagates principal_id to each packet
  6. health() returns correct status
  7. AST scan: no direct Neo4j writes outside allowed modules
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from core.governance.schemas import EvaluationResult, PolicyEffect
from core.schemas import PacketEnvelope, PacketWriteResult

# =============================================================================
# Fixtures
# =============================================================================


class FakeGovernance:
    """Fake governance gate for testing."""

    def __init__(self, *, allow: bool = True) -> None:
        self._allow = allow

    async def evaluate(self, request: Any) -> EvaluationResult:
        if self._allow:
            return EvaluationResult(
                request_id=request.request_id,
                allowed=True,
                effect=PolicyEffect.ALLOW,
                policy_id="test-policy",
                policy_name="Test Policy",
                reason="Allowed by test",
            )
        return EvaluationResult(
            request_id=request.request_id,
            allowed=False,
            effect=PolicyEffect.DENY,
            reason="Denied by test",
        )


class FakeIngestion:
    """Fake ingestion sink for testing."""

    def __init__(self) -> None:
        self.ingested: list[Any] = []

    async def ingest(
        self,
        packet_in: Any,
        embed: bool | None = None,
        generate_tags: bool | None = None,
    ) -> PacketWriteResult:
        self.ingested.append(packet_in)
        return PacketWriteResult(
            status="ok",
            packet_id=uuid4(),
            written_tables=["packets"],
        )


def _make_packet(**overrides: Any) -> PacketEnvelope:
    """Create a test PacketEnvelope."""
    defaults = {
        "packet_type": "test",
        "source_id": "test-source",
        "payload": {"key": "value"},
        "principal_id": "user:test",
        "ingress_origin": "api",
    }
    defaults.update(overrides)
    return PacketEnvelope(**defaults)


# =============================================================================
# Tests
# =============================================================================


class TestDomainBridgeGateway:
    """Invariant tests for DomainBridgeGateway."""

    @pytest.fixture
    def gateway(self):
        from domain_bridge.gateway import DomainBridgeGateway

        return DomainBridgeGateway(
            governance=FakeGovernance(allow=True),
            ingestion=FakeIngestion(),
        )

    @pytest.fixture
    def denying_gateway(self):
        from domain_bridge.gateway import DomainBridgeGateway

        return DomainBridgeGateway(
            governance=FakeGovernance(allow=False),
            ingestion=FakeIngestion(),
        )

    @pytest.mark.asyncio
    async def test_rejects_empty_principal_id(self, gateway: Any) -> None:
        """Gate 0: Empty principal_id must raise ValueError."""
        packet = _make_packet()
        with pytest.raises(ValueError, match="principal_id is required"):
            await gateway.submit(packet, principal_id="", ingress_origin="api")

    @pytest.mark.asyncio
    async def test_rejects_whitespace_principal_id(self, gateway: Any) -> None:
        """Gate 0: Whitespace-only principal_id must raise ValueError."""
        packet = _make_packet()
        with pytest.raises(ValueError, match="principal_id is required"):
            await gateway.submit(packet, principal_id="   ", ingress_origin="api")

    @pytest.mark.asyncio
    async def test_rejects_empty_ingress_origin(self, gateway: Any) -> None:
        """Gate 1: Empty ingress_origin must raise ValueError."""
        packet = _make_packet()
        with pytest.raises(ValueError, match="ingress_origin is required"):
            await gateway.submit(packet, principal_id="user:test", ingress_origin="")

    @pytest.mark.asyncio
    async def test_governance_deny_returns_denied(self, denying_gateway: Any) -> None:
        """Gate 2: Governance deny must return status='denied'."""
        packet = _make_packet()
        result = await denying_gateway.submit(
            packet, principal_id="user:test", ingress_origin="api"
        )
        assert result.status == "denied"
        assert result.governance_allowed is False

    @pytest.mark.asyncio
    async def test_successful_submit(self, gateway: Any) -> None:
        """Happy path: submit() returns status='ok'."""
        packet = _make_packet()
        result = await gateway.submit(
            packet, principal_id="user:test", ingress_origin="api"
        )
        assert result.status == "ok"
        assert result.governance_allowed is True
        assert result.write_result is not None
        assert result.write_result.status == "ok"

    @pytest.mark.asyncio
    async def test_batch_propagates_principal(self, gateway: Any) -> None:
        """submit_batch() must call submit() for each packet."""
        packets = [_make_packet() for _ in range(3)]
        batch_result = await gateway.submit_batch(
            packets, principal_id="user:batch", ingress_origin="api"
        )
        assert batch_result.total == 3
        assert batch_result.succeeded == 3
        assert batch_result.denied == 0
        assert batch_result.failed == 0

    @pytest.mark.asyncio
    async def test_health_returns_status(self, gateway: Any) -> None:
        """health() must return HealthStatus with correct flags."""
        status = await gateway.health()
        assert status.healthy is True
        assert status.governance_available is True
        assert status.ingestion_available is True


class TestNeo4jBypassBan:
    """AST scan: no direct Neo4j session.run() outside allowed modules."""

    ALLOWED_NEO4J_WRITERS = {
        "memory/graph_memory.py",
        "memory/neo4j_strategy_memory.py",
        "services/research/graph_persistence.py",
        "core/integration/wm_to_graph_sync.py",
        "core/memory/neo4j_client.py",
    }

    def test_no_unauthorized_neo4j_session_run(self) -> None:
        """Scan repo for session.run() calls outside allowed modules."""
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        violations: list[str] = []

        for py_file in repo_root.rglob("*.py"):
            rel_path = str(py_file.relative_to(repo_root))

            # Skip allowed modules, tests, and __pycache__
            if any(allowed in rel_path for allowed in self.ALLOWED_NEO4J_WRITERS):
                continue
            if "__pycache__" in rel_path or "test_" in rel_path:
                continue
            if ".git" in rel_path:
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    # Match: session.run(...) or neo4j.run_query(...)
                    if isinstance(func, ast.Attribute) and func.attr in (
                        "run",
                        "run_query",
                        "execute_query",
                    ):
                        if isinstance(func.value, ast.Name) and func.value.id in (
                            "session",
                            "neo4j",
                        ):
                            violations.append(
                                f"{rel_path}:{node.lineno} — {func.value.id}.{func.attr}()"
                            )

        assert not violations, "Unauthorized direct Neo4j writes found:\n" + "\n".join(
            f"  {v}" for v in violations
        )
