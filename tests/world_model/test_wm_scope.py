"""
L9 Tests - WorldModelRepository RLS Scope
Version: 1.0.0

Covers:
- _ensure_scope rejects missing tenant/org/user
- set_session_scope executes l9_set_scope
"""

import importlib.util

import pytest

from core.decorators import must_stay_async


def _get_repository_class():
    if importlib.util.find_spec("world_model.repository") is None:
        pytest.skip(
            "world_model.repository not available in test environment.",
            allow_module_level=False,
        )
    from world_model.repository import WorldModelRepository

    return WorldModelRepository


class FakeConnection:
    def __init__(self):
        self.execute_calls = []

    @must_stay_async("callers use await")
    async def execute(self, query: str, *args):
        self.execute_calls.append((query, args))


@pytest.mark.asyncio
async def test_set_session_scope_executes_rls_call():
    repo = _get_repository_class()()
    conn = FakeConnection()

    await repo.set_session_scope(
        conn,
        tenant_id="tenant-id",
        org_id="org-id",
        user_id="user-id",
        role="end_user",
    )

    assert conn.execute_calls, "Expected l9_set_scope to be executed"
    query, args = conn.execute_calls[0]
    assert "l9_set_scope" in query
    assert args == ("tenant-id", "org-id", "user-id", "end_user")


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_ensure_scope_rejects_missing_values():
    repo_class = _get_repository_class()
    with pytest.raises(RuntimeError):
        repo_class._ensure_scope(None, "org-id", "user-id")

    with pytest.raises(RuntimeError):
        repo_class._ensure_scope("tenant-id", None, "user-id")

    with pytest.raises(RuntimeError):
        repo_class._ensure_scope("tenant-id", "org-id", None)
