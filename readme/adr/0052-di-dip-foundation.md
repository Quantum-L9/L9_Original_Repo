# ADR 0052: Dependency Injection and Inversion (DI/DIP) Foundation

## Status
Accepted

## Pattern
Use Dependency Injection (DI) and Dependency Inversion Principle (DIP) with protocol-based abstractions and a lightweight DI container for all major subsystems.

## Files
- `core/abstractions/` — Protocol definitions
- `core/di/container.py` — DI container implementation
- `config/di_config.py` — Substrate bindings configuration

## Import Block
```python
# Protocols
from core.abstractions import (
    CacheClient,
    GraphClient,
    VectorStore,
    MemoryRepository,
    ObservabilityService,
    ToolExecutor,
)

# DI Container
from core.di.container import DIContainer, get_di_container

# Configuration
from config.di_config import configure_di_container
```

## Minimal Implementation
```python
# 1. Define protocol (core/abstractions/cache_protocols.py)
from typing import Protocol, runtime_checkable

@runtime_checkable
class CacheClient(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, ttl: int = 0) -> bool: ...
    async def delete(self, key: str) -> bool: ...

# 2. Create implementation
class RedisCacheClient:
    async def get(self, key: str) -> bytes | None:
        return await self._redis.get(key)
    # ... other methods

# 3. Bind in DI container (config/di_config.py)
def configure_di_container(container: DIContainer) -> DIContainer:
    container.bind_singleton(CacheClient, create_redis_client)
    return container

# 4. Resolve dependency
container = get_di_container()
cache = container.resolve(CacheClient)
```

## Usage Example
```python
# In a service that needs cache
class MyService:
    def __init__(self, cache: CacheClient):
        self._cache = cache
    
    async def get_data(self, key: str) -> dict:
        cached = await self._cache.get(key)
        if cached:
            return json.loads(cached)
        # ... fetch from source

# Resolve with injected dependencies
container = get_di_container()
service = container.resolve(MyService)  # cache auto-injected
```

## Anti-Pattern Example
```python
# ❌ WRONG — Direct singleton usage, tight coupling
from runtime.redis_client import get_redis_singleton

class MyService:
    def __init__(self):
        self._cache = get_redis_singleton()  # Hidden dependency!

# ✅ CORRECT — Explicit dependency injection
from core.abstractions import CacheClient

class MyService:
    def __init__(self, cache: CacheClient):  # Explicit, testable
        self._cache = cache
```

## Rules
1. **Depend on protocols, not implementations** — Use `CacheClient` not `RedisClient`
2. **Constructor injection** — Pass dependencies via `__init__`
3. **No hidden globals** — Don't call singletons inside constructors
4. **Bind at composition root** — Configure DI in `config/di_config.py`
5. **Test with mocks** — Inject mock implementations in tests

## DI Container Features
- **Singleton lifetime** — One instance per type
- **Transient lifetime** — New instance per resolve
- **Auto-injection** — Resolves constructor dependencies
- **Thread-safe** — Uses RLock for concurrent access
- **Circular detection** — Prevents infinite loops

## Rollback Strategy
```bash
# Disable DI container
export L9_DI_ENABLED=false

# Use backward-compatible helpers
from config.di_config import get_cache_client
cache = get_cache_client()  # Falls back to singleton
```

## AI Guidance
**DO:**
- Define protocols in `core/abstractions/`
- Use constructor injection for dependencies
- Bind implementations in `config/di_config.py`
- Write tests with mock implementations

**DO NOT:**
- Call singletons directly in business logic
- Depend on concrete implementations
- Create circular dependencies
- Skip protocol definitions for major subsystems

## Related ADRs
- [ADR-0026: Protocol-Based Abstractions](./0026-protocol-based-abstractions.md)
- [ADR-0053: Kernel Config Externalization](./0053-kernel-config-externalization.md)
