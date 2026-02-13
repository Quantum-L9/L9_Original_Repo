from unittest.mock import AsyncMock, MagicMock

import pytest

from core.decorators import must_stay_async


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_dispatch_tool_call_rejects_unknown_args_before_executor_runs():
    from core.tools.base_registry import (
        ToolMetadata,
        ToolRegistry,
        ToolSchema,
        ToolType,
    )
    from core.tools.registry_adapter import ExecutorToolRegistry

    registry = ToolRegistry()
    registry.register(
        ToolMetadata(
            id="demo_tool",
            name="Demo Tool",
            description="demo",
            tool_type=ToolType.CUSTOM,
            input_schema=ToolSchema(
                type="object",
                properties={"query": {"type": "string"}},
                required=["query"],
            ),
        ),
        executor=MagicMock(),
    )

    # execute_tool exists on ToolRegistry; patch it so we can assert it is not called
    registry.execute_tool = AsyncMock(
        return_value={"success": True, "result": "ok", "duration_ms": 1}
    )

    adapter = ExecutorToolRegistry(base_registry=registry, governance_enabled=False)

    result = await adapter.dispatch_tool_call(
        tool_id="demo_tool",
        arguments={"query": "hi", "oops": "bad"},
        context={"agent_id": "L", "task_id": "t1"},
    )

    assert result.success is False
    assert "unknown field" in (result.error or "").lower()
    registry.execute_tool.assert_not_called()
