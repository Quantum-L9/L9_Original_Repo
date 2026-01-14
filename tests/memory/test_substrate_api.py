from __future__ import annotations

import pytest

pytest.skip("Legacy memory substrate system — skipping.", allow_module_level=True)

"""
L9 Tests - Memory Substrate API
Version: 1.0.0

These tests assume a TEST_DATABASE_URL env var pointing at a
throwaway Postgres instance with migrations applied.
"""

import os

import pytest

from core.schemas import PacketEnvelopeIn
from memory.substrate_service import init_service, close_service


TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def service():
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set; skipping substrate API tests.")
    svc = await init_service(TEST_DB_URL)
    yield svc
    await close_service()


async def test_write_packet_success(service):
    packet_in = PacketEnvelopeIn(
        packet_type="event",
        payload={"test": "value"},
    )
    result = await service.write_packet(packet_in)
    assert result.status == "ok"
    assert result.packet_id is not None


async def test_get_packet_roundtrip(service):
    packet_in = PacketEnvelopeIn(
        packet_type="event",
        payload={"hello": "world"},
    )
    result = await service.write_packet(packet_in)
    envelope = await service.get_packet(result.packet_id)
    assert envelope is not None
    assert envelope.payload["hello"] == "world"
