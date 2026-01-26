# ADR 0010: must_stay_async Decorator

## Status

Accepted

## Pattern

`@must_stay_async(reason)` marks functions that MUST remain async even without await; prevents AI "fixes".

## Files

- `core/decorators.py` - Decorator definition
- All files using the decorator (50+ functions)

## Problem Solved

AI code reviewers flag async functions without `await` as "unnecessary async":

```python
# AI sees this and wants to remove async
async def get_service():  # "No await, remove async"
    return _service       # But callers use await!
```

## Solution

```python
from core.decorators import must_stay_async

@must_stay_async("callers use await")
async def get_service():
    return _service  # Decorator documents why async required
```

## Common Reasons

| Reason                         | Use Case             |
| ------------------------------ | -------------------- |
| `"callers use await"`          | Singleton getters    |
| `"FastAPI/ASGI route handler"` | Route handlers       |
| `"LangGraph node callback"`    | Graph nodes          |
| `"Protocol requires async"`    | Interface compliance |
| `"Future async operations"`    | Planned async work   |

## Files Using This Pattern

```
api/server.py               @must_stay_async("FastAPI/ASGI route handler")
memory/substrate_service.py @must_stay_async("callers use await")
world_model/runtime.py      @must_stay_async("callers use await")
world_model/engine.py       @must_stay_async("callers use await")
agents/research_agent_impl.py @must_stay_async("callers use await")
memory/checkpoint/postgres_saver.py @must_stay_async("callers use await")
```

## Decorator Implementation

```python
def must_stay_async(reason: str) -> Callable[[F], F]:
    """Marker decorator documenting why function must remain async."""
    def decorator(func: F) -> F:
        func.__must_stay_async__ = True
        func.__must_stay_async_reason__ = reason
        return func
    return decorator
```

## Rules

1. Use on async functions without await that must stay async
2. Always provide meaningful `reason` string
3. Decorator is documentation, not enforcement
4. AI reviewers MUST respect this decorator

## AI Guidance

**DO:**

- Read the `reason` before suggesting changes
- Keep async on decorated functions
- Add decorator when creating async getters

**DO NOT:**

- Remove `async` from `@must_stay_async` functions
- Remove the decorator itself
- Flag these as "unnecessary async"
- Suggest "simplifying" to sync functions
