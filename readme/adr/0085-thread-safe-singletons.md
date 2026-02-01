# ADR-0085: Thread-Safe Singleton Pattern

**Status:** Accepted  
**Date:** 2026-01-31  
**Source:** Bug Audit PR #81  

## Context

Singleton patterns that use simple `if instance is None` checks have race conditions in concurrent environments. Multiple threads can pass the check simultaneously and create multiple instances.

## Decision

**All singleton initialization MUST use double-checked locking with a threading/asyncio lock.**

### Forbidden Pattern

```python
# BAD - race condition
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        _instance = create_expensive_instance()
    return _instance
```

### Required Pattern (Sync)

```python
# GOOD - thread-safe with double-checked locking
import threading

_instance = None
_lock = threading.Lock()

def get_instance():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:  # Double-check inside lock
                _instance = create_expensive_instance()
    return _instance
```

### Required Pattern (Async)

```python
# GOOD - async-safe with double-checked locking
import asyncio

_instance = None
_lock = asyncio.Lock()

async def get_instance():
    global _instance
    if _instance is None:
        async with _lock:
            if _instance is None:  # Double-check inside lock
                _instance = await create_expensive_instance()
    return _instance
```

## Enforcement

- **Semgrep rule:** `l9-singleton-requires-lock` in `.semgrep/l9-rules.yaml`
- **CI gate:** Warning (manual review required)
- **Scope:** `core/`, `runtime/`, `services/`

## Risk Assessment: Startup-Only Singletons

Many L9 singletons are **initialized during application startup** before the event loop accepts concurrent requests. For these, the race condition is theoretical:

| Risk Level | Pattern | Action |
|------------|---------|--------|
| **HIGH** | Lazy init in request handlers | FIX - add locking |
| **MEDIUM** | Lazy init in background tasks | FIX when practical |
| **LOW** | Module-level init at import time | ACCEPT - no concurrency |
| **LOW** | Startup-phase init (lifespan) | ACCEPT - sequential startup |

**Current Warning Count:** ~37 singletons flagged
**Priority:** LOW - most are startup-only patterns

**When to add `# nosemgrep:`:**
- Startup-only patterns in lifespan/startup events
- Module-level initialization (runs at import)
- Prefer leaving warnings as technical debt tracking

## Consequences

- Thread-safe singleton initialization
- No duplicate expensive object creation
- Safe for concurrent access in FastAPI async handlers
