import sys
from pathlib import Path
import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.schemas import PacketEnvelopeIn

_gate_spec = importlib.util.spec_from_file_location(
    "l9_memory_governance_gate", ROOT / "memory" / "governance_gate.py"
)
_gate_module = importlib.util.module_from_spec(_gate_spec)
sys.modules[_gate_spec.name] = _gate_module
assert _gate_spec.loader is not None
_gate_spec.loader.exec_module(_gate_module)

build_governance_context = _gate_module.build_governance_context
enforce_packet_governance = _gate_module.enforce_packet_governance
ensure_governance_context = _gate_module.ensure_governance_context


def test_build_governance_context_blocks_cursor_private_scope():
    with pytest.raises(RuntimeError):
        build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            project_id="l9",
            allowed_scopes=["developer", "l-private"],
        )


def test_enforce_packet_governance_rejects_client_metadata():
    ctx = build_governance_context(
        caller_id="L",
        role="end_user",
        scope="developer",
        project_id="l9",
        allowed_scopes=["developer"],
    )
    packet = PacketEnvelopeIn(
        packet_type="memory.test",
        payload={"content": "hello"},
        metadata={"caller": "C"},
    )
    with pytest.raises(RuntimeError):
        enforce_packet_governance(packet, ctx)


@pytest.mark.asyncio
async def test_ensure_governance_context_uses_env_fallback(monkeypatch):
    monkeypatch.setenv("L9_MEMORY_CALLER_ID", "system")
    monkeypatch.setenv("L9_PROJECT_ID", "l9")
    monkeypatch.setenv("L9_MEMORY_SCOPE", "shared")

    async with ensure_governance_context("test"):
        pass
