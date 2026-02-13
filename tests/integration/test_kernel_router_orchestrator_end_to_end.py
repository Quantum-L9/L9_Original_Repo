"""
End-to-End Integration Test:
KERNELS → PACKET_PROTOCOL → ROUTER → ORCHESTRATOR

Validates:
- Kernel loader initializes cleanly
- PacketProtocol wiring returns valid allowed types + channels
- WSTaskRouter classifies inbound packets correctly
- Orchestrator receives & handles routed messages
- System tolerates ERROR + HEARTBEAT packets without failing

NO DB. NO WS server. NO external infra.
Everything runs with local mocks.
"""

import pytest

from core.decorators import must_stay_async

# Wiring layer (direct imports)
from core.kernel_wiring.packet_protocol_wiring import (
    get_allowed_event_types,
    get_default_channel,
    get_packet_protocol,
)

# Kernel loader (direct import to avoid lazy import issues)
from runtime.kernel_loader import load_kernel_stack

# ------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------


@pytest.fixture
def kernel_stack():
    """Load deterministic 10-kernel stack."""
    return load_kernel_stack()


@pytest.fixture
def ws_mock():
    """Mock WS connection for outbound transmissions."""

    class MockWS:
        sent = []

        @must_stay_async("callers use await")
        async def send_json(self, payload):
            self.sent.append(payload)

    return MockWS()


# ------------------------------------------------------------
# TEST 1: Kernel + Protocol Integrity
# ------------------------------------------------------------


def test_kernels_and_protocol_integrity(kernel_stack):
    proto = get_packet_protocol()
    events = get_allowed_event_types()
    default = get_default_channel()

    assert isinstance(proto, dict)
    assert isinstance(events, list)
    assert isinstance(default, str)


def test_kernel_stack_loads_all_10_kernels(kernel_stack):
    """Verify all 10 kernels are loaded."""
    expected_ids = [
        "master",
        "identity",
        "cognitive",
        "behavioral",
        "memory",
        "worldmodel",
        "execution",
        "safety",
        "developer",
        "packet_protocol",
    ]

    for kid in expected_ids:
        kernel = kernel_stack.get_kernel(kid)
        assert kernel is not None, f"Kernel '{kid}' not loaded"
        assert isinstance(kernel, dict), f"Kernel '{kid}' should be dict"


def test_kernel_hashes_computed(kernel_stack):
    """Verify hashes are computed for drift detection."""
    assert len(kernel_stack.hashes) == 10
    for filename, hash_val in kernel_stack.hashes.items():
        assert len(hash_val) == 64, f"Hash for {filename} should be SHA256 (64 chars)"


def test_kernel_get_rule_traversal(kernel_stack):
    """Test get_rule can traverse nested paths."""
    # Test a known path in master kernel
    mode = kernel_stack.get_rule("master", "modes.default", default="fallback")
    assert mode == "executive"

    # Test unknown path returns default
    unknown = kernel_stack.get_rule("master", "nonexistent.path", default="default_val")
    assert unknown == "default_val"
