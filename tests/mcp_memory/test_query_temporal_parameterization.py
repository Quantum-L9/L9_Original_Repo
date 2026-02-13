import os
import sys
from pathlib import Path

import pytest

from core.decorators import must_stay_async

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.path = [p for p in sys.path if not (p and Path(p).resolve().name == "tests")]
sys.modules.pop("memory", None)

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("MEMORY_DSN", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MCP_API_KEY_L", "test-key")

MCP_ROOT = PROJECT_ROOT / "mcp_memory"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from src.routes import memory_unified

from memory.governance_gate import (
    build_governance_context,
    governance_context,
)


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_query_temporal_uses_parameterized_kinds(monkeypatch) -> None:
    captured = {}

    async def _fake_fetch_all(query, *params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(memory_unified, "fetch_all", _fake_fetch_all)

    ctx = build_governance_context(
        caller_id="L",
        role="end_user",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer", "global", "l-private"],
    )

    injection = "fact'); DROP TABLE packet_store; --"
    async with governance_context(ctx):
        await memory_unified.query_temporal(
            user_id="l9-shared",
            kinds=[injection],
        )

    assert injection not in captured["query"]
    assert injection in captured["params"][-1][0]
