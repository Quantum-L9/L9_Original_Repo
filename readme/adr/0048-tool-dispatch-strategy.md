# ADR 0048: Tool Dispatch Strategy

## Status

Proposed

## Pattern

Decompose `_dispatch_tool_call` into three collaborating services: **ToolBindingService** (binding check), **ToolExecutionStrategy** (execution), and **ToolAuditService** (persistence/audit). Different execution strategies enable testing, simulation, and production modes.

## Context

L9's `_dispatch_tool_call` method handles too many concerns:

- Binding check
- Memory context binding
- Approval check
- Kernel-aware guarded execute
- Persistence to substrate + Redis
- ToolGraph audit
- World-model insight emission

This makes the method long (~200 lines) and hard to customize for different modes.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/tools/dispatch/__init__.py`
- `core/tools/dispatch/binding_service.py`
- `core/tools/dispatch/execution_strategy.py`
- `core/tools/dispatch/audit_service.py`
- `core/tools/dispatch/strategies/kernel_guarded_strategy.py`
- `core/tools/dispatch/strategies/direct_registry_strategy.py`
- `core/tools/dispatch/strategies/recorded_replay_strategy.py`

### Files to Modify

- `core/agents/executor.py` - Use dispatch services

## Import Block

```python
from typing import Protocol, runtime_checkable

from core.tools.dispatch import (
    ToolBindingService,
    ToolExecutionStrategy,
    ToolAuditService,
)
from core.tools.dispatch.strategies import (
    KernelGuardedStrategy,
    DirectRegistryStrategy,
    RecordedReplayStrategy,
)
```

## Minimal Implementation

```python
# core/tools/dispatch/binding_service.py
"""Tool binding verification service."""

from typing import Protocol, runtime_checkable
import logging

logger = logging.getLogger(__name__)


@runtime_checkable
class ToolBindingProtocol(Protocol):
    """Protocol for tool binding services."""

    def ensure_bound(self, instance, tool_call) -> None:
        """Ensure tool is bound to instance. Raises if not bound."""
        ...


class ToolBindingService:
    """
    Verifies tool bindings before execution.

    Checks:
    - Tool exists in registry
    - Tool is bound to agent instance
    - Required permissions are present
    """

    def __init__(self, tool_registry):
        self._registry = tool_registry

    def ensure_bound(self, instance, tool_call) -> None:
        """Verify tool is bound and permitted."""
        tool_name = tool_call.get("name")

        # Check tool exists
        tool_def = self._registry.get_tool(tool_name)
        if not tool_def:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        # Check binding
        if not instance.has_tool_binding(tool_name):
            raise ToolNotBoundError(f"Tool not bound to instance: {tool_name}")

        logger.debug(f"Tool binding verified: {tool_name}")
```

```python
# core/tools/dispatch/execution_strategy.py
"""Tool execution strategy protocols and implementations."""

from typing import Protocol, runtime_checkable, Any
import logging

logger = logging.getLogger(__name__)


@runtime_checkable
class ToolExecutionStrategy(Protocol):
    """Protocol for tool execution strategies."""

    async def execute(
        self,
        instance,
        tool_call: dict,
        memory_ctx: dict,
    ) -> Any:
        """Execute tool and return result."""
        ...
```

```python
# core/tools/dispatch/strategies/kernel_guarded_strategy.py
"""Kernel-guarded tool execution strategy (production)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KernelGuardedStrategy:
    """
    Production execution strategy with kernel guards.

    Features:
    - Kernel-aware permission checks
    - Approval gate integration
    - Full audit trail

    Use for: Production deployments
    """

    def __init__(self, kernel, approval_manager, tool_executor):
        self._kernel = kernel
        self._approval_manager = approval_manager
        self._executor = tool_executor

    async def execute(
        self,
        instance,
        tool_call: dict,
        memory_ctx: dict,
    ) -> Any:
        """Execute with kernel guards."""
        tool_name = tool_call.get("name")

        # Check kernel permissions
        if not self._kernel.permits_tool(tool_name, instance.agent_id):
            raise ToolPermissionDenied(f"Kernel denies tool: {tool_name}")

        # Check approval gate
        approval = await self._approval_manager.check(tool_name)
        if approval.requires_approval and not approval.is_approved:
            raise ToolApprovalRequired(f"Tool requires approval: {tool_name}")

        # Execute with context
        result = await self._executor.execute_tool(
            tool_name=tool_name,
            args=tool_call.get("arguments", {}),
            context=memory_ctx,
        )

        logger.info(f"Tool executed (kernel-guarded): {tool_name}")
        return result
```

```python
# core/tools/dispatch/strategies/direct_registry_strategy.py
"""Direct registry execution strategy (testing/local)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DirectRegistryStrategy:
    """
    Direct execution strategy bypassing guards.

    Features:
    - No kernel checks
    - No approval gates
    - Minimal overhead

    Use for: Testing, local development
    """

    def __init__(self, tool_registry):
        self._registry = tool_registry

    async def execute(
        self,
        instance,
        tool_call: dict,
        memory_ctx: dict,
    ) -> Any:
        """Execute directly from registry."""
        tool_name = tool_call.get("name")

        tool = self._registry.get_tool(tool_name)
        result = await tool.execute(
            **tool_call.get("arguments", {}),
        )

        logger.debug(f"Tool executed (direct): {tool_name}")
        return result
```

```python
# core/tools/dispatch/strategies/recorded_replay_strategy.py
"""Recorded replay execution strategy (simulation/offline)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RecordedReplayStrategy:
    """
    Replay execution from recorded results.

    Features:
    - No actual execution
    - Returns pre-recorded results
    - Deterministic replay

    Use for: Simulation, offline analysis, testing
    """

    def __init__(self, recording_store):
        self._store = recording_store

    async def execute(
        self,
        instance,
        tool_call: dict,
        memory_ctx: dict,
    ) -> Any:
        """Replay recorded result."""
        tool_name = tool_call.get("name")
        call_hash = self._compute_hash(tool_call)

        # Look up recorded result
        recorded = await self._store.get(call_hash)
        if recorded:
            logger.debug(f"Replaying recorded result: {tool_name}")
            return recorded["result"]

        # No recording found
        raise RecordingNotFoundError(f"No recording for: {tool_name}")

    def _compute_hash(self, tool_call: dict) -> str:
        """Compute deterministic hash for tool call."""
        import hashlib
        import json

        content = json.dumps(tool_call, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
```

```python
# core/tools/dispatch/audit_service.py
"""Tool audit service for recording executions."""

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class ToolAuditProtocol(Protocol):
    """Protocol for tool audit services."""

    async def record_success(self, tool_call, result, instance) -> None:
        """Record successful execution."""
        ...

    async def record_failure(self, tool_call, error, instance) -> None:
        """Record failed execution."""
        ...


class ToolAuditService:
    """
    Records tool executions for audit trail.

    Persists to:
    - Memory substrate (packets)
    - Redis (recent cache)
    - ToolGraph (for analysis)
    - World model (insights)
    """

    def __init__(
        self,
        substrate_service,
        redis_client,
        tool_graph,
        world_model,
    ):
        self._substrate = substrate_service
        self._redis = redis_client
        self._tool_graph = tool_graph
        self._world_model = world_model

    async def record_success(self, tool_call, result, instance) -> None:
        """Record successful tool execution."""
        tool_name = tool_call.get("name")

        # Emit packet
        await self._substrate.ingest_packet({
            "kind": "TOOL_EXECUTION",
            "author": instance.agent_id,
            "content": {
                "tool_name": tool_name,
                "arguments": tool_call.get("arguments"),
                "result_type": type(result).__name__,
                "status": "success",
            },
        })

        # Update Redis cache
        await self._redis.lpush(
            f"tool_calls:{instance.agent_id}",
            tool_name,
        )

        # Update ToolGraph
        await self._tool_graph.record_execution(tool_name, success=True)

        # Emit world model insight
        await self._world_model.emit_tool_insight(tool_name, result)

        logger.debug(f"Recorded success: {tool_name}")

    async def record_failure(self, tool_call, error, instance) -> None:
        """Record failed tool execution."""
        tool_name = tool_call.get("name")

        await self._substrate.ingest_packet({
            "kind": "TOOL_FAILURE",
            "author": instance.agent_id,
            "content": {
                "tool_name": tool_name,
                "error": str(error),
                "status": "failed",
            },
        })

        await self._tool_graph.record_execution(tool_name, success=False)

        logger.warning(f"Recorded failure: {tool_name} - {error}")
```

## Usage Example

```python
# Refactored _dispatch_tool_call

class AgentExecutorService:
    def __init__(
        self,
        binding_service: ToolBindingService,
        execution_strategy: ToolExecutionStrategy,
        audit_service: ToolAuditService,
        ...
    ):
        self._binding = binding_service
        self._execution = execution_strategy
        self._audit = audit_service

    async def _dispatch_tool_call(
        self,
        instance,
        tool_call: dict,
        memory_ctx: dict,
    ):
        """Dispatch tool call through services."""
        try:
            # 1. Verify binding
            self._binding.ensure_bound(instance, tool_call)

            # 2. Execute via strategy
            result = await self._execution.execute(
                instance, tool_call, memory_ctx
            )

            # 3. Record success
            await self._audit.record_success(tool_call, result, instance)

            return result

        except Exception as e:
            # Record failure
            await self._audit.record_failure(tool_call, e, instance)
            raise


# Production: Kernel-guarded strategy
executor = ExecutorBuilder()
    .with_dependency("binding_service", ToolBindingService(registry))
    .with_dependency("execution_strategy", KernelGuardedStrategy(kernel, approval, executor))
    .with_dependency("audit_service", ToolAuditService(...))
    .build()

# Testing: Direct registry strategy
executor = ExecutorBuilder()
    .with_dependency("execution_strategy", DirectRegistryStrategy(mock_registry))
    .build()

# Simulation: Recorded replay strategy
executor = ExecutorBuilder()
    .with_dependency("execution_strategy", RecordedReplayStrategy(recording_store))
    .build()
```

## Anti-Pattern Example

```python
# ❌ WRONG — Everything in one method
async def _dispatch_tool_call(self, instance, tool_call, memory_ctx):
    # Binding check (buried)
    tool = self._registry.get_tool(tool_call["name"])
    if not instance.has_binding(tool_call["name"]):
        raise ToolNotBoundError()

    # Approval check (buried)
    if tool.requires_approval:
        approval = await self._approval_manager.check(...)
        if not approval.is_approved:
            raise ToolApprovalRequired()

    # Execute (buried)
    result = await tool.execute(**tool_call["arguments"])

    # Persistence (buried)
    await self._substrate.ingest_packet(...)
    await self._redis.lpush(...)
    await self._tool_graph.record(...)
    await self._world_model.emit(...)

    return result

# ✅ CORRECT — Three collaborating services
self._binding.ensure_bound(instance, tool_call)
result = await self._execution.execute(instance, tool_call, memory_ctx)
await self._audit.record_success(tool_call, result, instance)
```

## Rules

1. Tool dispatch MUST use three services: binding, execution, audit
2. Execution strategies MUST implement `ToolExecutionStrategy` protocol
3. Production MUST use `KernelGuardedStrategy`
4. Tests MAY use `DirectRegistryStrategy` or `RecordedReplayStrategy`
5. Audit service MUST record both success and failure
6. Binding check MUST happen before execution
7. Audit MUST happen after execution (success or failure)

## AI Guidance

**DO:**

- Use strategy pattern for different execution modes
- Inject strategies via builder
- Record all executions via audit service
- Use DirectRegistryStrategy in tests

**DO NOT:**

- Bypass binding check
- Skip audit on failure
- Use DirectRegistryStrategy in production
- Mix execution and audit logic

## Related ADRs

- [ADR-0017: Tool Definition Schema](./0017-tool-definition-schema.md) - Tool definitions
- [ADR-0013: Governance Authority Hierarchy](./0013-governance-authority-hierarchy.md) - Approval gates
- [ADR-0022: Registry Pattern](./0022-registry-pattern.md) - Tool registry
