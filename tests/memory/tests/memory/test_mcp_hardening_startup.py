import os
import sys
import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_memory"))

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("MEMORY_DSN", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MCP_API_KEY_L", "test-lcto-key-all-scopes")
os.environ.setdefault("MCP_API_KEY_C", "test-cursor-key-dev-global")


from mcp_memory.src.main import (
    is_non_dev_environment,
    should_fail_hardening_disabled,
    should_fail_hardening_disabled_async,
)


def test_is_non_dev_environment():
    assert is_non_dev_environment("production") is True
    assert is_non_dev_environment("Development") is False
    assert is_non_dev_environment("test") is False


def test_should_fail_hardening_disabled():
    assert should_fail_hardening_disabled("production", False) is True
    assert should_fail_hardening_disabled("development", False) is False
    assert should_fail_hardening_disabled("production", True) is False


@pytest.mark.asyncio
async def test_should_fail_hardening_disabled_async():
    result = await should_fail_hardening_disabled_async("production", False)
    assert result is True
