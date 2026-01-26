# L9 Dependency Injection Bootstrap Guide

## Overview

The L9 DI container now includes a comprehensive `bootstrap_di_container()` function that initializes all core services in the correct dependency order. This guide explains how to use the bootstrap pattern in your applications.

## Quick Start

### 1. Bootstrap at Application Startup

```python
from core.di.container import bootstrap_di_container, set_global_di_container

# Bootstrap all services
container = await bootstrap_di_container()

# Make available globally
set_global_di_container(container)
```

### 2. Use in Your Application

```python
from core.di.container import get_global_di_container
from memory.substrate_service import MemorySubstrateService

# Get global container
container = get_global_di_container()

# Resolve services
memory_service = container.resolve(MemorySubstrateService)
```

### 3. Cleanup at Shutdown

```python
# Cleanup all resources
container.clear_all()
```

## FastAPI Integration

The recommended pattern for FastAPI applications:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.di.container import bootstrap_di_container, set_global_di_container

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = await bootstrap_di_container()
    set_global_di_container(container)

    yield

    # Shutdown
    container.clear_all()

app = FastAPI(lifespan=lifespan)
```

See `examples/fastapi_lifespan_di_bootstrap.py` for a complete example.

## Bootstrap Tiers

The bootstrap function initializes services in dependency order:

### Tier 1: Database Clients

- **PostgresClient** (required)
- **Neo4jClient** (optional)
- **RedisClient** (optional)

### Tier 2: Memory Substrate

- **MemorySubstrateService** (fully composed with all dependencies)

### Tier 3: Registries & Runtime

- **ToolRegistry** (optional)
- **AgentRegistry** (optional)
- **AIOSRuntime** (optional)

### Tier 4: Kernel

- **KernelProtocol** (with fallback strategy)

### Tier 5: Persistence & Validation

- **AgentPersistenceService**
- **PacketValidator**

### Tier 6: Telemetry

- **TelemetryService**

## Configuration

### Environment Variables

The bootstrap function reads configuration from environment variables:

```bash
# Required
DATABASE_URL=postgresql://localhost/l9

# Optional
NEO4J_URL=bolt://localhost:7687
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
```

### Programmatic Configuration

You can also pass configuration directly:

```python
container = await bootstrap_di_container(
    database_url="postgresql://localhost/l9",
    embedding_provider="openai",
    fallback_kernel="l9-core-v1",
    config={
        "NEO4J_URL": "bolt://localhost:7687",
        "REDIS_URL": "redis://localhost:6379",
        "OPENAI_API_KEY": "sk-...",
    }
)
```

## Error Handling

The bootstrap function provides clear error messages:

### Connection Errors

```python
try:
    container = await bootstrap_di_container()
except ConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    # Handle gracefully (e.g., retry, fallback)
```

### Runtime Errors

```python
try:
    container = await bootstrap_di_container()
except RuntimeError as e:
    logger.error(f"Service initialization failed: {e}")
    # Handle gracefully
```

## Testing

### Unit Tests

Mock the bootstrap function in your tests:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_feature():
    with patch("core.di.container.bootstrap_di_container") as mock_bootstrap:
        mock_container = AsyncMock()
        mock_bootstrap.return_value = mock_container

        # Your test code
        container = await bootstrap_di_container()
        assert container is mock_container
```

### Integration Tests

Use a test database for integration tests:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_bootstrap():
    container = await bootstrap_di_container(
        database_url="postgresql://localhost/l9_test"
    )

    try:
        # Test with real services
        service = container.resolve(MemorySubstrateService)
        assert service is not None
    finally:
        container.clear_all()
```

## Migration from Legacy Code

### Before (Legacy Pattern)

```python
from memory.substrate_service import create_substrate_service

# Creates short-lived container per call
service = await create_substrate_service(
    database_url="postgresql://localhost/l9"
)
```

### After (Bootstrap Pattern)

```python
from core.di.container import bootstrap_di_container, set_global_di_container

# Bootstrap once at startup
container = await bootstrap_di_container()
set_global_di_container(container)

# Resolve from global container
service = container.resolve(MemorySubstrateService)
```

## Benefits

1. **Single Initialization**: All services initialized once at startup
2. **Proper Lifecycle**: Cleanup callbacks ensure graceful shutdown
3. **Dependency Order**: Services initialized in correct order
4. **Error Handling**: Clear error messages for debugging
5. **Testing**: Easy to mock and test
6. **Performance**: No repeated initialization overhead

## Best Practices

### DO ✅

- Bootstrap once at application startup
- Use global container for long-running processes
- Register cleanup callbacks for resources
- Handle errors gracefully with retries
- Use environment variables for configuration

### DON'T ❌

- Bootstrap multiple times in the same process
- Create short-lived containers for each request
- Ignore connection errors
- Skip cleanup at shutdown
- Hard-code configuration values

## Troubleshooting

### Container Not Initialized

**Problem**: `get_global_di_container()` returns `None`

**Solution**: Call `set_global_di_container()` after bootstrap

```python
container = await bootstrap_di_container()
set_global_di_container(container)  # Don't forget this!
```

### Service Not Found

**Problem**: `BindingNotFoundError` when resolving service

**Solution**: Check that service is registered in bootstrap tiers

```python
# Check available services
container = get_global_di_container()
print(container._bindings.keys())
```

### Connection Failures

**Problem**: `ConnectionError` during bootstrap

**Solution**: Verify database is running and credentials are correct

```bash
# Test connection manually
psql postgresql://localhost/l9

# Check environment variables
echo $DATABASE_URL
```

## Advanced Usage

### Custom Bootstrap

You can create custom bootstrap functions for specific use cases:

```python
async def bootstrap_test_container() -> DIContainer:
    """Bootstrap container with test doubles."""
    container = DIContainer()

    # Register test doubles
    container.bind_singleton(MemorySubstrateService, lambda: MockMemoryService())
    container.bind_singleton(ToolRegistry, lambda: MockToolRegistry())

    return container
```

### Partial Bootstrap

For lightweight applications, you can bootstrap only required services:

```python
async def bootstrap_minimal_container() -> DIContainer:
    """Bootstrap only database and memory services."""
    container = DIContainer()

    # Tier 1: Database
    postgres = PostgresClient(database_url)
    await postgres.connect()
    container.bind_singleton(PostgresClient, lambda: postgres)

    # Tier 2: Memory
    memory = await create_substrate_service(database_url)
    container.bind_singleton(MemorySubstrateService, lambda: memory)

    return container
```

## Reference

- **Source**: `core/di/container.py`
- **Example**: `examples/fastapi_lifespan_di_bootstrap.py`
- **Tests**: `tests/unit/test_di_bootstrap.py`
- **ADR**: ADR-0052 (Dependency Injection)
- **Design Doc**: "DUAL DELIVERY: Docstring Edits + Wiring Sketch"

## Support

For questions or issues:

1. Check the examples directory
2. Review the test suite
3. Consult ADR-0052
4. Open an issue on GitHub
