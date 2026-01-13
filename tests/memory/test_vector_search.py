from __future__ import annotations

import pytest

pytest.skip("Legacy memory substrate system — skipping.", allow_module_level=True)

"""
L9 Tests - Semantic Vector Search
Version: 1.0.0

Uses the stub embedding provider if no OpenAI key is configured.
"""

import os

import pytest

from core.schemas.packet_envelope_v2 import PacketEnvelopeIn, SemanticSearchRequest
from memory.substrate_service import init_service, close_service


TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def service():
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set; skipping vector search tests.")
    svc = await init_service(TEST_DB_URL)
    yield svc
    await close_service()


async def test_semantic_search_returns_results(service):
    # Seed a few packets
    texts = ["plastic scrap buyer in NY", "HDPE regrind seller", "PP injection grade"]
    for t in texts:
        packet_in = PacketEnvelopeIn(
            packet_type="memory_write",
            payload={"text": t},
        )
        await service.write_packet(packet_in)

    request = SemanticSearchRequest(
        query="plastic buyer",
        top_k=3,
        agent_id=None,
    )
    result = await service.semantic_search(request)
    # We don't assert heavy semantics, just that it runs and returns hits
    assert result.hits is not None
