import os
import sys
from pathlib import Path

import pytest

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

from src import mcp_server  # noqa: E402
from src.mcp_server import MCPToolCall, handle_tool_call  # noqa: E402


class DummyCaller:
    def __init__(self, caller_id: str) -> None:
        self.caller_id = caller_id

    @property
    def creator(self) -> str:
        return "Cursor-IDE" if self.caller_id == "C" else "L-CTO"

    @property
    def source(self) -> str:
        return "cursor" if self.caller_id == "C" else "l9-kernel"


@pytest.mark.asyncio
async def test_cursor_cannot_write_l_private(monkeypatch) -> None:
    async def _noop_execute(*_args, **_kwargs):
        return None

    monkeypatch.setattr(mcp_server, "execute", _noop_execute)

    tool_call = MCPToolCall(
        name="save_memory",
        arguments={
            "content": "secret",
            "kind": "fact",
            "duration": "long",
            "scope": "l-private",
        },
    )

    with pytest.raises(ValueError, match="Scope not authorized for caller"):
        await handle_tool_call(tool_call, "l9-shared", DummyCaller("C"))
