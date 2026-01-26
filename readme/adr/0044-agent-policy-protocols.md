# ADR 0044: Agent Policy Protocols

## Status

Proposed

## Pattern

Extract cross-cutting concerns from `AgentExecutorService` into **injectable policy objects** that implement protocol interfaces. Each policy handles one concern and can be swapped per deployment.

## Context

L9's `AgentExecutorService` buries cross-cutting concerns:

- Prompt injection handling
- Graph hydration
- Memory warming
- Active memory encoding
- Self-reflection + kernel evolution

These are currently methods on the executor class, making them difficult to test, customize, or disable.

**Source:** Perplexity Refactor Analysis (2026-01-20)

## Files

### New Files to Create

- `core/agents/policies/__init__.py` - Policy exports
- `core/agents/policies/prompt_defense_policy.py` - Prompt injection protection
- `core/agents/policies/memory_warm_policy.py` - Memory warming
- `core/agents/policies/graph_hydration_policy.py` - Graph hydration
- `core/agents/policies/reflection_policy.py` - Self-reflection

### Files to Modify

- `core/agents/executor.py` - Inject policies via builder

## Import Block

```python
from typing import Protocol, Optional, runtime_checkable

from core.agents.policies import (
    PromptDefensePolicy,
    MemoryWarmPolicy,
    GraphHydrationPolicy,
    ReflectionPolicy,
)
from core.agents.schemas import AgentTask, ExecutionResult
from core.agents.agent_instance import AgentInstance
```

## Minimal Implementation

```python
# core/agents/policies/prompt_defense_policy.py
"""Prompt defense policy protocol and implementation."""

from typing import Optional, Protocol, runtime_checkable

from core.agents.schemas import AgentTask, ExecutionResult


@runtime_checkable
class PromptDefenseProtocol(Protocol):
    """Protocol for prompt defense policies."""

    async def check(self, task: AgentTask) -> Optional[ExecutionResult]:
        """
        Check task for prompt injection.

        Returns:
            None if safe, ExecutionResult with blocked status if injection detected.
        """
        ...


class PromptDefensePolicy:
    """
    Default prompt defense implementation.

    Checks for:
    - Known injection patterns
    - Suspicious character sequences
    - Role confusion attempts
    """

    def __init__(self, strict: bool = False):
        self._strict = strict

    async def check(self, task: AgentTask) -> Optional[ExecutionResult]:
        """Check task for prompt injection."""
        from core.agents.prompt_defense import detect_injection

        is_injection, confidence, pattern = detect_injection(
            task.payload.get("message", ""),
            strict=self._strict,
        )

        if is_injection:
            return ExecutionResult(
                status="blocked",
                output=None,
                error=f"Prompt injection detected: {pattern}",
                metadata={"confidence": confidence, "pattern": pattern},
            )

        return None  # Safe to proceed
```

```python
# core/agents/policies/memory_warm_policy.py
"""Memory warming policy protocol and implementation."""

from typing import Protocol, runtime_checkable

from core.agents.schemas import AgentTask


@runtime_checkable
class MemoryWarmProtocol(Protocol):
    """Protocol for memory warming policies."""

    async def warm(self, task: AgentTask) -> None:
        """Pre-load relevant memories for the task."""
        ...


class MemoryWarmPolicy:
    """
    Default memory warming implementation.

    Pre-loads:
    - Recent conversation context
    - Relevant past solutions
    - User preferences
    """

    def __init__(self, substrate_service=None):
        self._substrate = substrate_service

    async def warm(self, task: AgentTask) -> None:
        """Pre-load relevant memories."""
        if not self._substrate:
            return

        # Warm semantic cache with task context
        await self._substrate.warm_cache(
            query=task.payload.get("message", ""),
            thread_id=task.thread_id,
            limit=10,
        )
```

```python
# core/agents/policies/graph_hydration_policy.py
"""Graph hydration policy protocol and implementation."""

from typing import Protocol, runtime_checkable

from core.agents.schemas import AgentTask
from core.agents.agent_instance import AgentInstance


@runtime_checkable
class GraphHydrationProtocol(Protocol):
    """Protocol for graph hydration policies."""

    async def hydrate(self, task: AgentTask, instance: AgentInstance) -> None:
        """Hydrate agent instance with graph context."""
        ...


class GraphHydrationPolicy:
    """
    Default graph hydration implementation.

    Loads into agent context:
    - Relevant graph nodes
    - Entity relationships
    - Recent graph changes
    """

    def __init__(self, graph_client=None):
        self._graph = graph_client

    async def hydrate(self, task: AgentTask, instance: AgentInstance) -> None:
        """Hydrate agent with graph context."""
        if not self._graph:
            return

        # Query relevant graph nodes
        context = await self._graph.get_context_for_task(
            task_type=task.kind,
            keywords=task.payload.get("message", "").split()[:10],
        )

        # Add to agent's working memory
        instance.context.update({"graph_context": context})
```

```python
# core/agents/policies/reflection_policy.py
"""Self-reflection policy protocol and implementation."""

from typing import Protocol, runtime_checkable

from core.agents.schemas import AgentTask, ExecutionResult
from core.agents.agent_instance import AgentInstance


@runtime_checkable
class ReflectionProtocol(Protocol):
    """Protocol for self-reflection policies."""

    async def run(
        self,
        task: AgentTask,
        result: ExecutionResult,
        instance: AgentInstance,
    ) -> None:
        """Run self-reflection after task completion."""
        ...


class ReflectionPolicy:
    """
    Default self-reflection implementation.

    After task completion:
    - Analyze execution quality
    - Extract learnings
    - Emit kernel evolution packets
    """

    def __init__(self, always_reflect: bool = False):
        self._always_reflect = always_reflect

    async def run(
        self,
        task: AgentTask,
        result: ExecutionResult,
        instance: AgentInstance,
    ) -> None:
        """Run self-reflection."""
        # Skip for trivial tasks unless always_reflect
        if not self._always_reflect and result.status == "completed":
            if len(result.tool_calls or []) < 2:
                return

        # Analyze and learn
        from core.agents.selfreflection import analyze_execution

        insights = await analyze_execution(
            task=task,
            result=result,
            instance=instance,
        )

        # Emit learning packets
        if insights:
            await instance.emit_learning_packet(insights)
```

## Usage Example

```python
# Refactored executor with injected policies

class AgentExecutorService:
    def __init__(
        self,
        config: ExecutorConfig,
        stages: list[LoopStage],
        policies: dict,
        **deps,
    ):
        self._config = config
        self._stages = stages

        # Injected policies (all optional)
        self._prompt_defense = policies.get("prompt_defense")
        self._memory_warm = policies.get("memory_warming")
        self._graph_hydration = policies.get("graph_hydration")
        self._reflection = policies.get("reflection")

    async def start_agent_task(
        self,
        task: AgentTask,
        instance: AgentInstance,
    ) -> ExecutionResult:
        """Execute task with policy hooks."""

        # 1. Prompt defense (optional)
        if self._prompt_defense:
            blocked = await self._prompt_defense.check(task)
            if blocked:
                return blocked

        # 2. Memory warming (optional)
        if self._memory_warm:
            await self._memory_warm.warm(task)

        # 3. Graph hydration (optional)
        if self._graph_hydration:
            await self._graph_hydration.hydrate(task, instance)

        # 4. Execute via stages
        result = await self._run_execution_loop(instance)

        # 5. Reflection (optional)
        if self._reflection:
            await self._reflection.run(task, result, instance)

        return result


# Building executor with policies via builder
executor = (
    ExecutorBuilder()
    .with_config(config)
    .with_stages([...])
    .with_prompt_defense(PromptDefensePolicy(strict=True))
    .with_memory_warming(MemoryWarmPolicy(substrate_service))
    .with_graph_hydration(GraphHydrationPolicy(graph_client))
    .with_reflection(ReflectionPolicy())
    .build()
)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Concerns buried in executor methods
class AgentExecutorService:
    async def start_agent_task(self, task, instance):
        # Prompt defense buried
        if self._detect_injection(task.payload):
            return ExecutionResult(status="blocked")

        # Memory warming buried
        await self._warm_memory(task)

        # Graph hydration buried
        await self._hydrate_graph(task, instance)

        # Execute
        result = await self._run_execution_loop(instance)

        # Reflection buried
        await self._reflect(task, result, instance)

        return result

# ✅ CORRECT — Policies injected, concern separated
if self._prompt_defense:
    blocked = await self._prompt_defense.check(task)
    if blocked:
        return blocked
```

## Rules

1. Each policy MUST implement its protocol interface
2. All policies MUST be optional (executor works without them)
3. Policies MUST be single-responsibility
4. Policy implementations MUST NOT depend on executor internals
5. Policies SHOULD be < 100 lines each
6. Policy files MUST be in `core/agents/policies/`
7. Policies MUST be injectable via `ExecutorBuilder`

## AI Guidance

**DO:**

- Create one policy per cross-cutting concern
- Keep policies independent of each other
- Inject dependencies (substrate, graph) via constructor
- Test policies in isolation

**DO NOT:**

- Put multiple concerns in one policy
- Access executor internals from policies
- Make policies depend on each other
- Skip policy protocols — always define the interface

## Related ADRs

- [ADR-0041: Executor Builder Pattern](./0041-executor-builder-pattern.md) - Policies injected via builder
- [ADR-0042: Execution Profiles](./0042-execution-profiles.md) - Profiles configure policies
- [ADR-0026: Protocol-Based Abstractions](./0026-protocol-based-abstractions.md) - Policy protocol pattern
