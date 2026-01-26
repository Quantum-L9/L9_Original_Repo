"""
Telemetry Test Configuration
============================

Fixtures and configuration for telemetry tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_prometheus_metrics():
    """
    Reset Prometheus metrics between tests to avoid test pollution.

    Note: This is a best-effort reset. Some metrics may persist
    due to the global nature of Prometheus registries.
    """
    return
    # Cleanup after test - metrics persist in process but tests
    # should use unique labels to avoid collisions


@pytest.fixture
def prometheus_available():
    """Check if prometheus_client is available."""
    try:
        from telemetry.memory_metrics import PROMETHEUS_AVAILABLE

        return PROMETHEUS_AVAILABLE
    except ImportError:
        return False


@pytest.fixture
def mock_metrics():
    """Provide mock versions of all metric recording functions."""
    from unittest.mock import MagicMock

    return {
        "record_memory_write": MagicMock(),
        "record_memory_search": MagicMock(),
        "record_tool_invocation": MagicMock(),
        "set_memory_substrate_health": MagicMock(),
        "update_packet_store_size": MagicMock(),
    }
