# ADR 0061: L9 Facade Pattern for Simplified API

## Status

Accepted (Updated 2026-02-02)

## Pattern

Unified facade (`L9`) providing simplified access to L9 subsystems without exposing internal complexity.

## Files

- `l9/facade.py` - Implementation (canonical location)
- `l9/__init__.py` - SDK exports
- `core/facade/` - Backwards compatibility shims (deprecated)

## Context

L9 has many subsystems (agents, memory, tools, mediator). New developers face a steep learning curve:

```python
# ❌ WRONG — Complex internal access
from core.agents.executor import AgentExecutorService
from memory.substrate_service import MemorySubstrateService
from core.tools.registry_adapter import ExecutorToolRegistry
from core.coordination.agent_mediator import get_agent_mediator

# User must understand all subsystems
executor = AgentExecutorService(...)
memory = await get_memory_substrate_service()
registry = ExecutorToolRegistry()
mediator = await get_agent_mediator()
# ... wire everything together ...
```

The Facade pattern provides a single, simplified entry point.

## Import Block

```python
# Preferred (SDK at root level)
from l9 import (
    L9,
    get_l9,
    run_task,
    execute_tool,
    query_memory,
)

# Legacy (backwards compatible, deprecated)
from core.facade import L9Facade, get_l9_facade
```

## Minimal Implementation

```python
from core.singleton_auto_registry import register_singleton

@register_singleton(
    category="core",
    lifecycle=SingletonLifecycle.LAZY,
    dependencies=["agent_mediator"],
    description="Simplified L9 API facade"
)
async def get_l9_facade() -> L9Facade:
    """Get singleton facade instance."""
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = L9Facade()
    return _facade_instance


class L9Facade:
    """Simplified facade for L9 AIOS operations."""

    async def initialize(self) -> None:
        """Initialize all subsystems."""
        self._mediator = await get_agent_mediator()
        self._tool_registry = registry.get("tool_registry")
        self._memory_client = MemoryClient()

    async def run_task(
        self,
        task: str,
        agent: str = "l-cto",
        timeout_seconds: int | None = None,
    ) -> Any:
        """Run task with specified agent."""
        if timeout_seconds:
            async with asyncio.timeout(timeout_seconds):
                return await self._agents[agent].run(task)
        return await self._agents[agent].run(task)

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute tool by name."""
        return await self._tool_registry.dispatch_tool_call(
            tool_id=tool_name,
            arguments=kwargs,
            agent_id="l9-facade"
        )

    async def query_memory(
        self,
        query: str,
        agent_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query memory substrate."""
        return await self._memory_client.search(
            query=query,
            agent_id=agent_id,
            limit=limit
        )

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: dict[str, Any],
    ) -> str:
        """Send message between agents via mediator."""
        return await self._mediator.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message=message
        )
```

## Usage Example

```python
from l9 import get_l9

# Get singleton facade
l9 = await get_l9()
await l9.initialize()

# Simple API — no subsystem knowledge required
result = await l9.run_task("Research async patterns", agent="l-cto")
memories = await l9.query_memory("What did we learn?")
await l9.execute_tool("slack_send", channel="#general", message="Done!")
await l9.send_message("research", "l-cto", {"status": "complete"})

# Quick functions for even simpler access
from l9 import run_task, query_memory
result = await run_task("Analyze code")
memories = await query_memory("patterns")
```

## Benefits

| Benefit                   | Impact                  |
| ------------------------- | ----------------------- |
| Reduced learning curve    | -70% for new developers |
| Unified entry point       | Single import           |
| Sensible defaults         | Works out of the box    |
| Internal changes isolated | Subsystems can evolve   |

## Rules

1. Facade MUST use `@register_singleton` (NOT simple `@singleton`)
2. Facade MUST NOT expose internal implementation details
3. All common operations MUST be accessible via facade
4. Facade methods MUST have sensible defaults
5. Facade MUST delegate to appropriate subsystems

## Anti-Pattern

```python
# ❌ WRONG — Exposing internals
class L9Facade:
    def get_executor_service(self): ...  # Leaks internal
    def get_substrate_repository(self): ...  # Leaks internal

# ✅ CORRECT — High-level operations only
class L9Facade:
    async def run_task(self, task, agent): ...
    async def query_memory(self, query): ...
    async def execute_tool(self, tool_name, **kwargs): ...
```

## AI Guidance

**DO:**

- Use facade for high-level L9 operations
- Initialize once, reuse singleton
- Use convenience functions for simple scripts

**DO NOT:**

- Expose internal subsystem access
- Use simple `@singleton` decorator
- Bypass facade for direct subsystem access (except in tests)
- Add low-level methods to facade

## Related ADRs

- [ADR-0004: Singleton Auto-Registry](./0004-singleton-auto-registry.md) - Singleton pattern
- [ADR-0047: Memory Facade Decomposition](./0047-memory-facade-decomposition.md) - Memory-specific facade
- [ADR-0060: Mediator Pattern](./0060-mediator-pattern-agent-communication.md) - Used internally
