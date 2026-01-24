"""
Golden-path integration test for memory packet ingestion.

Flow: API -> routing -> ingest_packet (stub) -> response.
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if "api" in sys.modules:
    del sys.modules["api"]
importlib.invalidate_caches()


@pytest.mark.asyncio
async def test_memory_packet_ingestion_golden_path(monkeypatch):
    """POST /api/v1/memory/packet returns PacketResponse on successful ingest."""
    tests_path = str(project_root / "tests")
    if tests_path in sys.path:
        sys.path.remove(tests_path)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if "api" in sys.modules:
        del sys.modules["api"]
    importlib.invalidate_caches()

    monkeypatch.setenv("L9_EXECUTOR_API_KEY", "test-key")

    from api.memory import router as memory_router
    from core.schemas import PacketWriteResult

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/v1/memory")

    packet_id = uuid4()
    mock_result = PacketWriteResult(
        packet_id=packet_id,
        status="ok",
        written_tables=["packet_store"],
        error_message=None,
    )

    mock_ingest = AsyncMock(return_value=mock_result)
    monkeypatch.setattr(memory_router, "ingest_packet", mock_ingest)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memory/packet",
            headers={"Authorization": "Bearer test-key"},
            json={
                "packet_type": "test_packet",
                "payload": {"hello": "world"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "packet_id": str(packet_id),
        "status": "ok",
        "written_tables": ["packet_store"],
        "error_message": None,
    }
    mock_ingest.assert_awaited_once()
