# ADR 0054: Loop Stage Protocol

## Status

Proposed

## Pattern

Decompose `_run_execution_loop` into discrete, testable **micro-stages** that follow a `LoopStage` protocol. Each stage is a single-responsibility unit that transforms a `LoopContext` and can be swapped, tested, or extended independently.

## Context

L9's `AgentExecutorService._run_execution_loop` is a ~300-line monolithic method that handles:

- Pre-governance checks
- Circuit breaker logic
- Tool shortlisting
- ReAct tracing
- Governance audit
- Loop control / max-iteration handling

This violates SRP and makes the loop difficult to test, extend, or customize per deployment profile.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/agents/stages/__init__.py` - Stage exports
- `core/agents/stages/loop_context.py` - LoopContext dataclass
- `core/agents/stages/base_stage.py` - LoopStage protocol
- `core/agents/stages/pre_governance_stage.py` - Authority + safety checks
- `core/agents/stages/tool_shortlist_stage.py` - Tool selection
- `core/agents/stages/aios_call_stage.py` - AIOS + circuit breaker
- `core/agents/stages/reaction_logging_stage.py` - ReAct THOUGHT/OBSERVATION packets
- `core/agents/stages/tool_dispatch_stage.py` - Tool execution
- `core/agents/stages/termination_guard_stage.py` - Max-iteration rules
- `core/agents/stages/governance_audit_stage.py` - Audit logging

### Files to Modify

- `core/agents/executor.py` - Refactor `_run_execution_loop` to use stages

## Import Block

```python
from typing import Optional, Protocol
from dataclasses import dataclass

from core.agents.stages import (
    LoopStage,
    LoopContext,
    PreGovernanceStage,
    ToolShortlistStage,
    AiosCallStage,
    ReactionLoggingStage,
    ToolDispatchStage,
    TerminationGuardStage,
    GovernanceAuditStage,
)
```

## Minimal Implementation

```python
# core/agents/stages/base_stage.py
"""Loop stage protocol for executor pipeline decomposition."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LoopStage(Protocol):
    """
    Protocol for execution loop stages.

    Each stage receives a LoopContext, performs one concern,
    and returns the (potentially modified) context.
    """

    async def run(self, ctx: "LoopContext") -> "LoopContext":
        """Execute this stage and return updated context."""
        ...
```

```python
# core/agents/stages/loop_context.py
"""Execution loop context passed between stages."""

from dataclasses import dataclass, field
from typing import Any, Optional

from core.agents.agent_instance import AgentInstance


@dataclass
class LoopContext:
    """
    Immutable context passed through the execution loop pipeline.

    Each stage reads from context and returns a new context
    with any modifications (functional style).
    """

    instance: AgentInstance
    aios_result: Optional[Any] = None
    status: str = "running"
    error: Optional[str] = None
    final_result: Optional[str] = None
    iteration: int = 0
    tool_calls: list = field(default_factory=list)

    def with_status(self, status: str) -> "LoopContext":
        """Return new context with updated status."""
        return LoopContext(
            instance=self.instance,
            aios_result=self.aios_result,
            status=status,
            error=self.error,
            final_result=self.final_result,
            iteration=self.iteration,
            tool_calls=self.tool_calls,
        )

    def with_error(self, error: str) -> "LoopContext":
        """Return new context with error and failed status."""
        return LoopContext(
            instance=self.instance,
            aios_result=self.aios_result,
            status="failed",
            error=error,
            final_result=self.final_result,
            iteration=self.iteration,
            tool_calls=self.tool_calls,
        )
```

## Usage Example

```python
# Refactored _run_execution_loop in executor.py

class AgentExecutorService:
    def __init__(self, ...):
        # Compose stages (can be injected via ExecutorBuilder)
        self._loop_stages: list[LoopStage] = [
            PreGovernanceStage(self._governance),
            ToolShortlistStage(self._tool_registry),
            AiosCallStage(self._aios_runtime, self._circuit_breaker),
            ReactionLoggingStage(self._substrate_service),
            ToolDispatchStage(self._tool_executor),
            TerminationGuardStage(max_iterations=self._max_iterations),
            GovernanceAuditStage(self._audit_logger),
        ]

    async def _run_execution_loop(
        self,
        instance: AgentInstance,
    ) -> ExecutionResult:
        """Execute agent loop using stage pipeline."""

        ctx = LoopContext(instance=instance)

        while ctx.status == "running":
            for stage in self._loop_stages:
                ctx = await stage.run(ctx)
                if ctx.status in {"completed", "failed", "blocked", "terminated"}:
                    break

            ctx = LoopContext(
                instance=ctx.instance,
                aios_result=ctx.aios_result,
                status=ctx.status,
                error=ctx.error,
                final_result=ctx.final_result,
                iteration=ctx.iteration + 1,
                tool_calls=ctx.tool_calls,
            )

        return ExecutionResult(
            output=ctx.final_result,
            status=ctx.status,
            error=ctx.error,
            tool_calls=ctx.tool_calls,
        )
```

## Anti-Pattern Example

```python
# ❌ WRONG — Monolithic execution loop (current state)
async def _run_execution_loop(self, instance: AgentInstance) -> ExecutionResult:
    for iteration in range(self._max_iterations):
        # Pre-governance (buried)
        if not await self._check_governance(instance):
            return ExecutionResult(status="blocked")

        # Tool shortlisting (buried)
        tools = await self._shortlist_tools(instance)

        # AIOS call (buried)
        try:
            result = await self._aios_runtime.execute(...)
        except CircuitBreakerOpen:
            return ExecutionResult(status="circuit_open")

        # ReAct logging (buried)
        await self._emit_react_packet(...)

        # Tool dispatch (buried)
        if result.tool_calls:
            for tool_call in result.tool_calls:
                await self._dispatch_tool_call(...)

        # ... 200 more lines of tangled logic ...

# ✅ CORRECT — Stage-based pipeline (this ADR)
async def _run_execution_loop(self, instance: AgentInstance) -> ExecutionResult:
    ctx = LoopContext(instance=instance)

    while ctx.status == "running":
        for stage in self._loop_stages:
            ctx = await stage.run(ctx)
            if ctx.status in {"completed", "failed", "blocked", "terminated"}:
                break

    return ExecutionResult.from_context(ctx)
```

## Rules

1. Each stage MUST implement the `LoopStage` protocol
2. Stages MUST be single-responsibility (one concern per stage)
3. Stages MUST NOT directly modify the context — return a new context
4. Stage order MUST be configurable (via `ExecutorBuilder` or DI)
5. Each stage MUST be independently testable with mock context
6. Terminal statuses: `completed`, `failed`, `blocked`, `terminated`
7. Context MUST carry all state needed by downstream stages
8. Stages SHOULD be < 100 lines each

## AI Guidance

**DO:**

- Create one stage per cross-cutting concern
- Pass all required data via `LoopContext`
- Test each stage in isolation with mock contexts
- Allow stage composition via builder pattern (see ADR-0041)
- Use functional style — stages return new context, don't mutate

**DO NOT:**

- Put multiple concerns in one stage
- Access executor internals from stages — inject dependencies
- Skip stages conditionally inside the loop — let stages handle their own skip logic
- Mutate context in place — return new context instance

## Related ADRs

- [ADR-0041: Executor Builder Pattern](./0041-executor-builder-pattern.md) - Composing stages via builder
- [ADR-0042: Execution Profiles](./0042-execution-profiles.md) - Different stage compositions
- [ADR-0009: Circuit Breaker Resilience](./0009-circuit-breaker-resilience.md) - Used in AiosCallStage
