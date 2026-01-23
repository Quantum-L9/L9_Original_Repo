# ADR 0004: Singleton Auto-Registry Pattern

## Status
Accepted

## Pattern
Services self-register via `@register_singleton` decorator; discovered at startup via module import.

## Files
- `core/singleton_auto_registry.py` - Decorator definitions
- `core/singleton_registry.py` - Registry implementation
- `api/server.py:611-635` - Discovery at startup
- All files with `@register_singleton` decorator

## Modules Using This Pattern
```
memory/substrate_service.py      @register_singleton(name="memory_substrate_service")
memory/retrieval.py              @register_singleton(name="retrieval_pipeline")
memory/ingestion.py              @register_singleton(name="ingestion_pipeline")
memory/insight_extraction.py     @register_singleton(name="insight_extraction")
memory/housekeeping.py           @register_singleton(name="housekeeping_service")
world_model/engine.py            @register_singleton(name="world_model_engine")
world_model/service.py           @register_singleton(name="world_model_service")
world_model/repository.py        @register_singleton(name="world_model_repository")
services/research/tools/tool_resolver.py  @register_singleton(name="tool_resolver")
services/research/memory_adapter.py       @register_singleton(name="memory_adapter")
```

## Rules
1. New singletons MUST use `@register_singleton` decorator
2. Decorator MUST specify `name`, `lifecycle`, `description`
3. Closer function uses `@register_singleton_closer(name)`
4. Discovery happens via module import in `api/server.py` startup
5. DO NOT add manual try/except blocks to `_register_core_singletons()`

## Decorator Syntax
```python
from core.singleton_auto_registry import register_singleton, register_singleton_closer

@register_singleton(
    name="my_service",
    lifecycle="lazy",  # or "startup", "manual"
    description="Service description"
)
async def get_my_service():
    return MyService()

@register_singleton_closer("my_service")
async def close_my_service():
    # cleanup
    pass
```

## Lifecycle Options
| Lifecycle | When Initialized | Use Case |
|-----------|------------------|----------|
| `startup` | At app start | Critical services |
| `lazy` | On first access | Most services |
| `manual` | Explicit call | Test fixtures |

## AI Guidance
**DO:**
- Use `@register_singleton` for new services
- Include `@register_singleton_closer` for cleanup
- Import module in `api/server.py` DISCOVERY_PACKAGES for auto-discovery

**DO NOT:**
- Add manual registration to `singleton_registry.py`
- Remove `@register_singleton` decorators (they're not "unused")
- Create multiple instances of decorated services
- Use `@register_singleton` on non-async functions without `lifecycle="manual"`
