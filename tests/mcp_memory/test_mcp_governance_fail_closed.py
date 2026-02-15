from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_call_tool_fails_closed_when_governance_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_DSN", "postgresql://test:test@localhost:5432/test")

    mcp_router = importlib.import_module("api.routes.mcp")

    monkeypatch.setattr(mcp_router, "_has_mcp", True)
    monkeypatch.setattr(mcp_router, "_has_governance", False)

    async def _verify_api_key_dep(_request, _auth):
        return SimpleNamespace(
            caller_id="L",
            user_id="u1",
            creator="L-CTO",
            source="l9-kernel",
        )

    monkeypatch.setattr(mcp_router, "_verify_api_key_dep", _verify_api_key_dep)

    class DummyRequest:
        def __init__(self) -> None:
            self.app = SimpleNamespace(state=SimpleNamespace())

        async def json(self):
            return {"tool_name": "memory.search", "arguments": {}}

    with pytest.raises(HTTPException) as exc_info:
        await mcp_router.call_tool(DummyRequest(), authorization="Bearer test")

    assert exc_info.value.status_code == 503
    assert "Governance gate unavailable" in exc_info.value.detail
