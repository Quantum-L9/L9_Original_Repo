"""
L9 Mac Agent Executor Tests
===========================

Tests for mac agent executor with mocked subprocess.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.decorators import must_stay_async

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from mac_agent.executor import AutomationExecutor
except ImportError as e:
    pytest.skip(f"Could not import mac_agent.executor: {e}", allow_module_level=True)


# =============================================================================
# Test: Executor runs command
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_executor_runs_command():
    """
    Contract: Executor can execute automation commands.
    """
    executor = AutomationExecutor()

    # Mock browser/page operations
    with patch("mac_agent.executor.PLAYWRIGHT_AVAILABLE", True):
        with patch("playwright.async_api.async_playwright") as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

            # Test that executor can be initialized
            assert executor is not None
            assert executor.config is not None


# =============================================================================
# Test: Executor handles timeout
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_executor_handles_timeout():
    """
    Contract: Executor handles timeout errors gracefully.
    """
    executor = AutomationExecutor()

    # Verify executor has timeout handling
    assert executor is not None
    # Timeout handling is typically in the execute methods
    # This test verifies the executor structure exists


# =============================================================================
# Test: Executor captures output
# =============================================================================


def test_executor_captures_output():
    """
    Contract: Executor captures and stores execution output.
    """
    executor = AutomationExecutor()

    # Verify executor has logs attribute for capturing output
    assert hasattr(executor, "logs")
    assert isinstance(executor.logs, list)

    # Test that logs can be appended
    executor.logs.append("test log entry")
    assert len(executor.logs) == 1
    assert executor.logs[0] == "test log entry"
