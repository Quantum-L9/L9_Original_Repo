# L9 Auto-Wiring System - Implementation Guide

**Version**: 1.0.0  
**Status**: Phase 1 - API Router Auto-Registration  
**Created**: 2026-01-18  

---

## 1. Overview

The L9 Auto-Wiring System eliminates manual component registration and wiring through a decorator-based auto-discovery framework. This guide covers Phase 1: API Router Auto-Registration.

### Key Benefits

- **Zero Boilerplate**: No more manual `app.include_router()` calls
- **Self-Documenting**: Routers declare their own metadata
- **Type-Safe**: Full type hints and validation
- **Observable**: Built-in snapshots and health checks
- **Fail-Fast**: Validation errors caught at startup

### What's Included in Phase 1

1. **Core `AutoRegistry` Framework** (`core/auto_registry.py`)
2. **Router Auto-Registration** (`api/router_registry.py`)
3. **Example Auto-Wired Router** (`api/routes/example_autowired.py`)
4. **Comprehensive Test Suite** (`tests/core/test_auto_registry.py`, `tests/api/test_router_registry.py`)

---

## 2. Quick Start

### Creating an Auto-Wired Router

```python
# api/routes/my_feature.py
from fastapi import APIRouter
from api.router_registry import register_router

@register_router(
    prefix="/api/v1/my-feature",
    name="my_feature",
    tags=["my-feature"],
    priority=10,
    module_display_name="My Feature Module"
)
def create_my_feature_router() -> APIRouter:
    """Create the my-feature router."""
    router = APIRouter()
    
    @router.get("/hello")
    async def hello():
        return {"message": "Hello from auto-wired router!"}
    
    return router
```

That's it! No need to modify `api/server.py` or any other files. The router will be automatically discovered and wired.

### Wiring Routers in server.py

```python
# api/server.py
from fastapi import FastAPI
from api.router_registry import discover_routers, wire_routers

app = FastAPI()

# Discover all routers in api.routes package
discover_routers("api.routes")

# Wire them to the app
wire_routers(app, module_registry=app.state.module_registry)
```

---

## 3. Core Concepts

### 3.1 AutoRegistry

The `AutoRegistry` class is a generic, type-safe registry that supports:

- **Decorator-based registration**: Components register themselves
- **Factory functions**: Lazy initialization of components
- **Priority ordering**: Control load order
- **Tag filtering**: Categorize and filter components
- **Validation**: Ensure components meet requirements
- **Discovery**: Automatic module scanning

### 3.2 Router Registry

The `router_registry` is a specialized instance of `AutoRegistry` for FastAPI routers. It:

- Validates that registered objects are `APIRouter` instances
- Stores router metadata (prefix, tags, priority)
- Integrates with `ModuleRegistry` for observability
- Provides `discover_routers()` and `wire_routers()` helpers

---

## 4. API Reference

### `@register_router()`

Decorator to register a FastAPI router for auto-wiring.

**Parameters:**
- `prefix` (str): URL prefix for the router (e.g., "/api/v1/users")
- `name` (Optional[str]): Router identifier (defaults to function name)
- `tags` (Optional[List[str]]): OpenAPI tags
- `priority` (int): Loading priority (higher = loaded first, default: 0)
- `module_display_name` (Optional[str]): Human-readable name for ModuleRegistry

**Example:**
```python
@register_router(prefix="/api/v1/users", tags=["users"], priority=10)
def create_users_router() -> APIRouter:
    router = APIRouter()
    # ... define routes ...
    return router
```

### `discover_routers(package: str) -> int`

Automatically discover all routers in the specified package.

**Parameters:**
- `package` (str): Python package to scan (e.g., "api.routes")

**Returns:**
- Number of modules discovered

**Example:**
```python
count = discover_routers("api.routes")
print(f"Discovered {count} router modules")
```

### `wire_routers(app: FastAPI, module_registry: Optional[ModuleRegistry] = None) -> int`

Wire all registered routers to the FastAPI application.

**Parameters:**
- `app` (FastAPI): FastAPI application instance
- `module_registry` (Optional[ModuleRegistry]): Optional ModuleRegistry for tracking

**Returns:**
- Number of routers wired

**Example:**
```python
app = FastAPI()
discover_routers("api.routes")
wire_routers(app, module_registry)
```

### `get_router_snapshot() -> dict`

Get a snapshot of all registered routers for observability.

**Returns:**
- Dictionary with registry statistics and component list

**Example:**
```python
snapshot = get_router_snapshot()
print(f"Registered routers: {snapshot['component_count']}")
```

---

## 5. Migration Guide

### Migrating Existing Routers

**Before (Manual Wiring):**
```python
# api/routes/users.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_users():
    return {"users": []}

# api/server.py
from api.routes.users import router as users_router
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
```

**After (Auto-Wiring):**
```python
# api/routes/users.py
from fastapi import APIRouter
from api.router_registry import register_router

@register_router(prefix="/api/v1/users", tags=["users"])
def create_users_router() -> APIRouter:
    router = APIRouter()
    
    @router.get("/")
    async def list_users():
        return {"users": []}
    
    return router

# api/server.py
# No changes needed! Router is auto-discovered and wired.
```

### Backward Compatibility

The auto-wiring system is **fully backward compatible**. You can:

1. Keep existing manual router includes in `server.py`
2. Gradually migrate routers to auto-wiring
3. Mix manual and auto-wired routers

---

## 6. Testing

### Running Tests

```bash
# Run all auto-wiring tests
PYTHONPATH=/home/ubuntu/L9:$PYTHONPATH python -m pytest tests/core/test_auto_registry.py tests/api/test_router_registry.py -v

# Run specific test
PYTHONPATH=/home/ubuntu/L9:$PYTHONPATH python -m pytest tests/api/test_router_registry.py::test_wire_routers_basic -v
```

### Writing Tests for Auto-Wired Routers

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.router_registry import wire_routers

def test_my_router():
    app = FastAPI()
    
    # Import your router module (triggers registration)
    from api.routes import my_feature
    
    # Wire routers
    wire_routers(app)
    
    # Test endpoints
    client = TestClient(app)
    response = client.get("/api/v1/my-feature/hello")
    assert response.status_code == 200
```

---

## 7. Best Practices

### 1. Use Factory Functions

Always use factory functions (not module-level routers) to enable lazy initialization:

✅ **Good:**
```python
@register_router(prefix="/api/v1/users")
def create_users_router() -> APIRouter:
    router = APIRouter()
    # ... setup ...
    return router
```

❌ **Avoid:**
```python
router = APIRouter()
# ... setup ...
register_router(prefix="/api/v1/users")(router)
```

### 2. Set Priorities for Load Order

Use priorities when routers have dependencies:

```python
@register_router(prefix="/api/v1/auth", priority=100)  # Load first
def create_auth_router(): ...

@register_router(prefix="/api/v1/users", priority=50)  # Load after auth
def create_users_router(): ...
```

### 3. Use Tags for Organization

Tag routers for filtering and documentation:

```python
@register_router(prefix="/api/v1/admin", tags=["admin", "internal"])
def create_admin_router(): ...
```

### 4. Provide Display Names

Always provide a `module_display_name` for ModuleRegistry integration:

```python
@register_router(
    prefix="/api/v1/users",
    module_display_name="User Management Module"
)
def create_users_router(): ...
```

---

## 8. Troubleshooting

### Router Not Discovered

**Problem**: Router not appearing in the app.

**Solutions**:
1. Ensure the module is in the scanned package (e.g., `api/routes/`)
2. Check that `discover_routers()` is called before `wire_routers()`
3. Verify the module doesn't start with `_` (private modules are skipped)
4. Check logs for import errors

### Duplicate Registration Error

**Problem**: `DuplicateRegistrationError` raised.

**Solution**: Each router must have a unique `name`. Either:
1. Provide explicit unique names: `@register_router(name="unique_name", ...)`
2. Use unique function names (default behavior)

### Router Not Working After Wiring

**Problem**: Endpoints return 404.

**Solutions**:
1. Check the `prefix` matches your expected URL
2. Verify `wire_routers()` was called
3. Check FastAPI logs for routing errors
4. Use `get_router_snapshot()` to inspect registered routers

---

## 9. Future Phases

The auto-wiring system will be extended to cover:

- **Phase 2**: Tool Executor Auto-Registration
- **Phase 3**: Agent Auto-Discovery
- **Phase 4**: Orchestrator Auto-Discovery
- **Phase 5**: MCP Server Auto-Registration

Each phase will follow the same pattern established in Phase 1.

---

## 10. Contributing

When adding new auto-wired routers:

1. Create router in `api/routes/`
2. Use `@register_router()` decorator
3. Add tests in `tests/api/`
4. Run `black` and `ruff` for formatting
5. Ensure all tests pass

---

## 11. References

- **Core Implementation**: `core/auto_registry.py`
- **Router Registry**: `api/router_registry.py`
- **Example Router**: `api/routes/example_autowired.py`
- **Tests**: `tests/core/test_auto_registry.py`, `tests/api/test_router_registry.py`
- **Analysis**: See `TOP_5_AUTOWIRING_OPPORTUNITIES.md` for full impact analysis
