# ADR 0011: Lazy Initialization Pattern

## Status
Accepted

## Pattern
Singletons created on first access via `get_*()` methods; cached in module-level `_instance` variable.

## Files
- All singleton services with `get_*()` functions
- `memory/substrate_service.py` - `get_service()`
- `world_model/engine.py` - `get_world_model_engine()`
- `memory/graph_client.py` - `get_graph_client()`

## Pattern Structure
```python
# Module-level cache
_service: Optional[MyService] = None

async def get_service() -> MyService:
    """Get singleton (lazy init on first call)."""
    global _service
    if _service is None:
        _service = await create_service()  # Created once
    return _service

async def close_service() -> None:
    """Close and clear singleton."""
    global _service
    if _service:
        await _service.close()
        _service = None
```

## Service Accessor Methods
| Service | Getter | Closer |
|---------|--------|--------|
| Memory Substrate | `get_service()` | `close_service()` |
| Neo4j Client | `get_graph_client()` | `close_graph_client()` |
| Redis Client | `get_redis_client()` | `close_redis_client()` |
| World Model | `get_world_model_engine()` | `close_world_model_engine()` |
| Query Classifier | `get_query_classifier()` | N/A |

## Class-Level Lazy Init
```python
class MemorySubstrateService:
    def __init__(self, ...):
        # Lazy-initialized modules
        self._query_classifier: Optional[QueryClassifier] = None
        
    def get_query_classifier(self) -> QueryClassifier:
        """Lazy initialization on first access."""
        if self._query_classifier is not None:
            return self._query_classifier
        self._query_classifier = QueryClassifier()
        return self._query_classifier
```

## Rules
1. First call creates, subsequent calls return cached
2. Always check `if _instance is None` before creating
3. Provide `close_*()` for cleanup
4. Use `Optional[Type]` for type hint
5. Log initialization on first create

## AI Guidance
**DO:**
- Use `get_*()` to access singletons
- Call `close_*()` on shutdown
- Check for None before accessing internals

**DO NOT:**
- Call constructors directly (use getter)
- Create multiple instances
- Remove None check "optimization"
- Eager-load at module import time
