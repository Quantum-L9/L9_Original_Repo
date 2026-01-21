"""
Integration tests for cross-substrate alignment.

Tests Postgres ↔ Neo4j consistency.
"""

import os
import pytest

pytest.importorskip("asyncpg")

from memory.graph_client import get_neo4j_client, close_neo4j_client
from memory.substrate_service import init_service, close_service

TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")


@pytest.fixture(scope="function")
async def substrate_service():
    """Provide a memory substrate service for integration tests."""
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL not set; skipping alignment tests.")
    service = await init_service(TEST_DB_URL)
    yield service
    await close_service()


@pytest.fixture(scope="function")
async def graph_client():
    """Provide a Neo4j client for alignment tests."""
    client = await get_neo4j_client()
    if client is None:
        pytest.skip("Neo4j client not available; skipping alignment tests.")
    yield client
    await close_neo4j_client()


class TestSubstrateAlignment:
    """Cross-substrate alignment tests."""

    @pytest.mark.asyncio
    async def test_postgres_to_neo4j_alignment(self, substrate_service, graph_client):
        """Verify Postgres packets have Neo4j nodes."""
        from memory.substrate_alignment import SubstrateAlignmentChecker

        checker = SubstrateAlignmentChecker(
            repository=substrate_service._repository,
            graph_client=graph_client,
        )

        report = await checker.check_postgres_to_neo4j(limit=100)

        assert (
            report.alignment_percentage >= 90.0
        ), f"Alignment below threshold: {report.alignment_percentage}%"

    @pytest.mark.asyncio
    async def test_neo4j_to_postgres_alignment(self, substrate_service, graph_client):
        """Verify Neo4j nodes have Postgres packets."""
        from memory.substrate_alignment import SubstrateAlignmentChecker

        checker = SubstrateAlignmentChecker(
            repository=substrate_service._repository,
            graph_client=graph_client,
        )

        report = await checker.check_neo4j_to_postgres(limit=100)

        assert len(report.errors) == 0, f"Errors during check: {report.errors}"

    @pytest.mark.asyncio
    async def test_full_alignment_check(self, substrate_service, graph_client):
        """Full bidirectional alignment check."""
        from memory.substrate_alignment import SubstrateAlignmentChecker

        checker = SubstrateAlignmentChecker(
            repository=substrate_service._repository,
            graph_client=graph_client,
        )

        report = await checker.check_alignment(limit=100)

        assert report.is_aligned or report.alignment_percentage >= 95.0


class TestQueryInjectionPrevention:
    """Tests for query injection detection."""

    @pytest.mark.asyncio
    async def test_sql_injection_blocked(self):
        """SQL injection patterns should be blocked."""
        from core.tools.memory_tools import _detect_query_injection

        malicious_queries = [
            "packet_store; DROP TABLE users; --",
            "SELECT * FROM users WHERE 1=1; DELETE FROM packet_store;",
            "TRUNCATE packet_store",
        ]

        for query in malicious_queries:
            assert _detect_query_injection(query) is True, f"Should block: {query}"

    @pytest.mark.asyncio
    async def test_cypher_injection_blocked(self):
        """Cypher injection patterns should be blocked."""
        from core.tools.memory_tools import _detect_query_injection

        malicious_queries = [
            "MATCH (n) DETACH DELETE n",
            "MATCH (n:User) DELETE n",
        ]

        for query in malicious_queries:
            assert _detect_query_injection(query) is True, f"Should block: {query}"

    @pytest.mark.asyncio
    async def test_benign_queries_allowed(self):
        """Normal search queries should pass."""
        from core.tools.memory_tools import _detect_query_injection

        benign_queries = [
            "What were the last GMP reports?",
            "Find all memory packets from yesterday",
            "Search for authentication patterns",
        ]

        for query in benign_queries:
            assert _detect_query_injection(query) is False, f"Should allow: {query}"


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker in batch endpoint."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker should open after threshold failures."""
        from api.memory.router import _batch_circuit_breaker

        _batch_circuit_breaker.reset()

        for i in range(10):
            _batch_circuit_breaker.record_failure(f"Simulated failure {i}")

        assert _batch_circuit_breaker.is_open() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """Circuit breaker should close after successful operation."""
        from api.memory.router import _batch_circuit_breaker
        from core.observability.circuit_breaker import CircuitBreakerState

        _batch_circuit_breaker._state = CircuitBreakerState.HALF_OPEN

        _batch_circuit_breaker.record_success()

        assert _batch_circuit_breaker.is_open() is False
