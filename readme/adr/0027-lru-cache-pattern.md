# ADR 0027: LRU Cache Pattern

## Status
Accepted

## Pattern
Use `@lru_cache` for expensive computations and config loading; cache config, not service instances.

## Files
- `config/rls_config.py` - `@lru_cache(maxsize=1)` for config
- `config/settings.py` - `@lru_cache(maxsize=1)` for settings
- `runtime/kernel_loader.py` - Kernel cache
- `core/kernels/prompt_builder.py` - Prompt cache

## Import Block
```python
from functools import lru_cache
from typing import TypeVar

T = TypeVar("T")
```

## Minimal Implementation
```python
from functools import lru_cache
from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass(frozen=True)  # frozen=True makes it hashable for cache
class RLSConfig:
    """Row-Level Security configuration."""
    tenant_id: str
    org_id: str
    user_id: str


@lru_cache(maxsize=1)
def get_rls_config() -> RLSConfig:
    """
    Get RLS config singleton. CACHED.
    
    First call loads from env/file, subsequent calls return cached.
    """
    return RLSConfig(
        tenant_id=os.getenv("L9_TENANT_ID", "default"),
        org_id=os.getenv("L9_ORG_ID", "default"),
        user_id=os.getenv("L9_USER_ID", "default"),
    )


@lru_cache(maxsize=1)
def get_settings() -> "Settings":
    """Load settings singleton. CACHED."""
    from config.settings import Settings
    return Settings()


@lru_cache(maxsize=10)
def load_kernel(kernel_name: str) -> dict:
    """
    Cache parsed kernel YAML.
    
    Args:
        kernel_name: Name of kernel file (without .yaml)
    
    Returns:
        Parsed kernel dict
    """
    path = Path("private/kernels/00_system") / f"{kernel_name}.yaml"
    return yaml.safe_load(path.read_text())


@lru_cache(maxsize=100)
def build_prompt(template_name: str, **kwargs) -> str:
    """Cache built prompts."""
    template = load_template(template_name)
    return template.format(**kwargs)
```

## Usage Example
```python
from functools import lru_cache
from config.rls_config import get_rls_config

# First call — loads config
config = get_rls_config()  # Cache MISS, loads from env

# Second call — returns cached
config = get_rls_config()  # Cache HIT, instant return

# Check cache stats
info = get_rls_config.cache_info()
print(info)  # CacheInfo(hits=1, misses=1, maxsize=1, currsize=1)

# Clear cache (e.g., on config reload)
get_rls_config.cache_clear()

# Next call reloads
config = get_rls_config()  # Cache MISS, reloads
```

## Anti-Pattern Example
```python
# ❌ WRONG — Caching service instance
@lru_cache(maxsize=1)
def get_substrate_service():
    return MemorySubstrateService()  # Service has mutable state!

# ❌ WRONG — Caching mutable objects
@lru_cache(maxsize=10)
def get_config_dict() -> dict:
    return {"key": "value"}  # Dict is mutable, can be modified!

# ❌ WRONG — No maxsize (defaults to 128, may grow unbounded)
@lru_cache
def expensive_computation(x):
    return x * 2

# ❌ WRONG — Caching DB results
@lru_cache(maxsize=100)
def get_user(user_id: str):  # DB data changes!
    return db.query(User).filter_by(id=user_id).first()

# ✅ CORRECT — Cache config (immutable)
@lru_cache(maxsize=1)
def get_rls_config() -> RLSConfig:  # Returns frozen dataclass
    return RLSConfig(...)

# ✅ CORRECT — Use Redis for DB caching
async def get_user_cached(user_id: str):
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    user = await db.get_user(user_id)
    await redis.setex(f"user:{user_id}", 300, json.dumps(user))
    return user
```

## When to Use
| Use Case | Cache? | maxsize | Why |
|----------|--------|---------|-----|
| Config loading | ✅ Yes | 1 | Singleton, rarely changes |
| Settings | ✅ Yes | 1 | Singleton, rarely changes |
| Kernel parsing | ✅ Yes | 10-20 | Limited set of kernels |
| Prompt building | ✅ Yes | 100 | Expensive computation |
| Service instances | ❌ No | — | Use lazy init pattern (ADR-0011) |
| DB query results | ❌ No | — | Use Redis/external cache |
| Mutable objects | ❌ No | — | Can be modified unexpectedly |

## Rules
1. Use `maxsize=1` for singletons
2. Cache MUST be deterministic (same input → same output)
3. Don't cache mutable objects
4. Don't cache service instances (use lazy init pattern)
5. Clear cache on config reload: `func.cache_clear()`

## AI Guidance
**DO:**
- Use `@lru_cache` for config/settings
- Set explicit `maxsize`
- Add "CACHED" in docstring for clarity
- Use `cache_clear()` for invalidation

**DO NOT:**
- Cache service instances (use `get_*()` pattern)
- Cache DB query results (use Redis)
- Cache mutable objects (dicts, lists)
- Forget maxsize (defaults to 128)
