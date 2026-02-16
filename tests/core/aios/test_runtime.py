"""
L9 AIOS Runtime Tests
=====================

Tests for AIOS runtime.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from core.agents.schemas import AIOSResult
    from core.aios.runtime import AIOSRuntime
except ImportError as e:
    pytest.skip(f"Could not import core.aios.runtime: {e}", allow_module_level=True)


# =============================================================================
# Test: Runtime initialization
# =============================================================================


def test_runtime_initialization():
    """
    Contract: AIOSRuntime can be instantiated.
    """
    with patch("core.aios.runtime.AsyncOpenAI"):
        runtime = AIOSRuntime(
            api_key="test-key",
            model="gpt-4o",
        )
        assert runtime is not None
        assert runtime.model == "gpt-4o"


# =============================================================================
# Test: Execute reasoning mock
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_execute_reasoning_mock():
    """
    Contract: AIOSRuntime can execute reasoning with mocked LLM.
    """
    with patch("core.aios.runtime.AsyncOpenAI") as mock_openai_class:
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_response.usage.total_tokens = 100

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        runtime = AIOSRuntime(api_key="test-key", model="gpt-4o")

        context = {
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [],
        }

        result = await runtime.execute_reasoning(context)

        assert isinstance(result, AIOSResult)
        assert result.result_type == "response"
        assert result.content == "Test response"
