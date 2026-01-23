# ADR 0033: Async Context Manager Pattern

## Status
Accepted

## Pattern
Use `@asynccontextmanager` for resource lifecycle; ensure cleanup in finally block.

## Files
- `api/server.py` - Lifespan context
- `memory/substrate_repository.py` - Transaction context
- `memory/governance_gate.py` - Governance context

## Import Block
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator, TypeVar

T = TypeVar("T")
```

## Minimal Implementation
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GovernanceScope:
    """Governance scope for RLS operations."""
    tenant_id: str
    org_id: str
    user_id: str
    active: bool = False
    
    async def activate(self) -> None:
        """Activate the governance scope."""
        self.active = True
    
    async def deactivate(self) -> None:
        """Deactivate the governance scope."""
        self.active = False


@asynccontextmanager
async def governance_context(
    tenant_id: str,
    org_id: str,
    user_id: str,
) -> AsyncIterator[GovernanceScope]:
    """
    Context manager for governance-scoped operations.
    
    Args:
        tenant_id: Tenant UUID
        org_id: Organization UUID
        user_id: User UUID
    
    Yields:
        Activated GovernanceScope
    
    Example:
        async with governance_context(tid, oid, uid) as scope:
            await do_work(scope)
    """
    scope = GovernanceScope(tenant_id, org_id, user_id)
    
    try:
        # Setup
        await scope.activate()
        logger.debug(
            "governance.scope_activated",
            tenant=tenant_id,
            user=user_id,
        )
        
        yield scope  # Caller uses scope here
        
    finally:
        # Cleanup (ALWAYS runs, even on exception)
        await scope.deactivate()
        logger.debug(
            "governance.scope_deactivated",
            tenant=tenant_id,
        )


@asynccontextmanager
async def managed_resource(
    resource_name: str,
) -> AsyncIterator[dict]:
    """
    Generic pattern for managed resources.
    
    Args:
        resource_name: Name for logging
    
    Yields:
        Resource dict
    """
    resource = {"name": resource_name, "active": False}
    
    try:
        # Acquire resource
        resource["active"] = True
        logger.info(f"{resource_name}.acquired")
        
        yield resource
        
    except Exception as e:
        # Log error before re-raising
        logger.error(
            f"{resource_name}.error",
            error=str(e),
        )
        raise
        
    finally:
        # Release resource (ALWAYS)
        resource["active"] = False
        logger.info(f"{resource_name}.released")
```

## Usage Example
```python
from memory.governance_gate import governance_context
from contextlib import asynccontextmanager

# Use governance context
async def process_with_governance():
    async with governance_context(
        tenant_id="abc-123",
        org_id="org-456",
        user_id="user-789",
    ) as scope:
        # Operations run within governance scope
        await do_work(scope)
        # Scope automatically deactivated after block


# FastAPI lifespan example
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context."""
    # Startup
    await init_database()
    await init_services()
    logger.info("app.startup_complete")
    
    yield  # App runs here
    
    # Shutdown (cleanup)
    await close_services()
    await close_database()
    logger.info("app.shutdown_complete")

app = FastAPI(lifespan=lifespan)


# Nested context managers
async def complex_operation():
    async with governance_context(...) as gov:
        async with transaction_context(...) as tx:
            async with lock_context(...) as lock:
                # All three active here
                await do_work(gov, tx, lock)
            # lock released
        # tx committed/rolled back
    # gov deactivated
```

## Anti-Pattern Example
```python
# ❌ WRONG — No finally block (cleanup may not run)
@asynccontextmanager
async def bad_context():
    resource = await acquire()
    yield resource
    await release(resource)  # Never runs if yield raises!

# ❌ WRONG — Cleanup not in finally
@asynccontextmanager
async def bad_context():
    try:
        resource = await acquire()
        yield resource
    except Exception:
        await release(resource)  # Misses normal exit!

# ❌ WRONG — Sync contextmanager for async
from contextlib import contextmanager

@contextmanager  # Wrong! Should be @asynccontextmanager
def sync_context():
    yield await async_resource()  # Can't await here!

# ✅ CORRECT — Always use try/finally
@asynccontextmanager
async def good_context():
    resource = await acquire()
    try:
        yield resource
    finally:
        await release(resource)  # ALWAYS runs
```

## Common Use Cases
| Context | Resource | Setup | Cleanup |
|---------|----------|-------|---------|
| Lifespan | App services | `init_services()` | `close_services()` |
| Transaction | DB connection | BEGIN | COMMIT/ROLLBACK |
| Governance | RLS scope | SET app.* | Clear session |
| Lock | Distributed lock | Acquire | Release |
| File | File handle | Open | Close |

## Rules
1. ALWAYS use try/finally in context manager
2. Cleanup code in finally block
3. Log entry/exit for debugging
4. Yield single value (or None)
5. Handle exceptions before re-raising

## AI Guidance
**DO:**
- Use `@asynccontextmanager` for async resources
- Put cleanup in `finally` block
- Log context entry/exit
- Yield minimal interface

**DO NOT:**
- Skip `finally` block
- Forget to cleanup on exception
- Yield mutable internal state
- Use sync `@contextmanager` for async
