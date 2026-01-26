# ADR 0022: Registry Pattern

## Status

Accepted

## Pattern

Domain objects registered in type-safe registries; discovered at startup via decorators or explicit registration.

## Files

- `core/tools/base_registry.py` - BaseRegistry[T] generic class
- `core/tools/registry_adapter.py` - ToolRegistry
- `agents/agent_registry.py` - AgentRegistry
- `orchestrators/registry.py` - OrchestratorRegistry

## Import Block

```python
from core.tools.base_registry import BaseRegistry
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
```

## Minimal Implementation

```python
from typing import TypeVar, Generic, Callable, Any
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

class BaseRegistry(Generic[T]):
    """
    Type-safe registry for domain objects.

    Usage:
        registry = BaseRegistry[ToolDefinition]()
        registry.register("my_tool", tool_definition)
        tool = registry.get("my_tool")
    """

    def __init__(self, validator: Callable[[T], bool] | None = None):
        self._registry: dict[str, T] = {}
        self._validator = validator

    def register(self, key: str, item: T) -> None:
        """Register an item with validation."""
        if self._validator and not self._validator(item):
            raise ValueError(f"Item {key} failed validation")

        if key in self._registry:
            logger.warning("registry.overwrite", key=key)

        self._registry[key] = item
        logger.debug("registry.registered", key=key)

    def get(self, key: str) -> T | None:
        """Get item by key, or None if not found."""
        return self._registry.get(key)

    def get_or_raise(self, key: str) -> T:
        """Get item by key, raise if not found."""
        item = self._registry.get(key)
        if item is None:
            raise KeyError(f"Item '{key}' not found in registry")
        return item

    def list_keys(self) -> list[str]:
        """List all registered keys."""
        return list(self._registry.keys())

    def list_items(self) -> list[T]:
        """List all registered items."""
        return list(self._registry.values())

    def __contains__(self, key: str) -> bool:
        return key in self._registry

    def __len__(self) -> int:
        return len(self._registry)


# Decorator for self-registration
def register_in(registry: BaseRegistry[T], key: str):
    """Decorator to register item in registry."""
    def decorator(item: T) -> T:
        registry.register(key, item)
        return item
    return decorator
```

## Usage Example

```python
from core.tools.base_registry import BaseRegistry, register_in
from core.tools.tool_graph import ToolDefinition

# Create typed registry
tool_registry = BaseRegistry[ToolDefinition](
    validator=lambda t: t.tool_id is not None
)

# Explicit registration
tool_registry.register("memory_search", ToolDefinition(
    tool_id="memory_search",
    name="Memory Search",
    description="Search memory",
))

# Decorator registration
@register_in(tool_registry, "git_commit")
def git_commit_tool():
    return ToolDefinition(
        tool_id="git_commit",
        name="Git Commit",
        description="Commit changes",
    )

# Usage
tool = tool_registry.get("memory_search")
if tool:
    result = await execute_tool(tool)

# Check existence
if "memory_search" in tool_registry:
    ...

# List all
for key in tool_registry.list_keys():
    print(f"Tool: {key}")
```

## Anti-Pattern Example

```python
# ❌ WRONG — Global dict instead of registry
TOOLS: dict[str, Any] = {}
TOOLS["my_tool"] = tool  # No validation, no typing

# ❌ WRONG — Multiple registries for same domain
tool_registry_1 = {}
tool_registry_2 = {}  # Duplicate!

# ❌ WRONG — Direct access to internal dict
registry._registry["key"] = value  # Bypasses validation

# ✅ CORRECT — Use BaseRegistry with proper typing
tool_registry = BaseRegistry[ToolDefinition]()
tool_registry.register("my_tool", tool)
```

## Registry Types

| Registry             | Domain              | Key      | Value Type       |
| -------------------- | ------------------- | -------- | ---------------- |
| ToolRegistry         | Tools               | tool_id  | ToolDefinition   |
| AgentRegistry        | Agents              | agent_id | AgentConfig      |
| OrchestratorRegistry | Orchestrators       | name     | OrchestratorBase |
| CellRegistry         | Collaborative Cells | cell_id  | CellDefinition   |

## Rules

1. Use `BaseRegistry[T]` for new domain registries
2. Include validator function for type safety
3. Discover via import at startup or decorator
4. Use `get_or_raise()` when item must exist
5. Never access `_registry` directly

## AI Guidance

**DO:**

- Use existing registries (don't create duplicates)
- Register via decorator or explicit `register()`
- Use `get_or_raise()` for required items
- Include validator for safety

**DO NOT:**

- Create duplicate registries for same domain
- Access `_registry` dict directly
- Use plain dicts instead of registries
- Skip validation on registration
