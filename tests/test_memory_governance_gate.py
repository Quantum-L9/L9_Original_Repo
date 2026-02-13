"""Tests for memory governance gate (GMP-68)."""

import importlib.util
import sys
from pathlib import Path

import pytest

from core.decorators import must_stay_async

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
    """Cursor (caller_id='C') cannot have l-private in allowed_scopes."""
    # GMP-103: Policy-based validation from config/policies/memory_scope.yaml
    with pytest.raises(RuntimeError, match="cannot access 'l-private' scope"):
        build_governance_context(
            caller_id="C",
            role="end_user",
            scope="developer",
            project_id="l9",
            allowed_scopes=["developer", "l-private"],
        )


def test_build_governance_context_allows_l_private_scope():
    """L-CTO (caller_id='L') can have l-private in allowed_scopes."""
    ctx = build_governance_context(
        caller_id="L",
        role="end_user",
        scope="l-private",
        project_id="l9",
        allowed_scopes=["developer", "l-private"],
    )
    assert ctx.caller_id == "L"
    assert "l-private" in ctx.allowed_scopes


def test_enforce_packet_governance_rejects_client_metadata():
    """Client-supplied metadata that conflicts with context is rejected."""
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
        metadata={"caller": "C"},  # Conflicts with ctx.caller_id="L"
    )
    with pytest.raises(RuntimeError, match="Client-supplied metadata"):
        enforce_packet_governance(packet, ctx)


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_ensure_governance_context_uses_env_fallback(monkeypatch):
    """Fallback context uses environment variables when no context set."""
    monkeypatch.setenv("L9_MEMORY_CALLER_ID", "system")
    monkeypatch.setenv("L9_PROJECT_ID", "l9")
    monkeypatch.setenv("L9_MEMORY_SCOPE", "shared")

    async with ensure_governance_context("test") as ctx:
        assert ctx.caller_id == "system"
        assert ctx.project_id == "l9"
        assert ctx.scope == "shared"
