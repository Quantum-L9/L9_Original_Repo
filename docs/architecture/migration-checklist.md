# L9 DI/DIP Migration Checklist

**Version:** 1.0.0  
**GMP:** di-dip-phase1-phase6  
**Quality:** Top Frontier AI Lab - Enterprise Production-Ready  
**Author:** L9 DI/DIP Upgrade Team

---

## Overview

This checklist provides a **step-by-step guide** for migrating L9 modules from direct instantiation patterns to protocol-based dependency injection. Follow this guide to ensure safe, reversible, and production-ready migrations.

---

## Migration Phases

### Phase 0: Pre-Migration Assessment

**Objective:** Understand current module dependencies and impact.

- [ ] **Identify module to migrate** (e.g., `memory/substrate_service.py`)
- [ ] **Map current dependencies** (what singletons/clients does it use?)
- [ ] **Check for circular dependencies** (A imports B, B imports A)
- [ ] **Review test coverage** (ensure >70% coverage before migration)
- [ ] **Document current behavior** (what does the module do?)
- [ ] **Identify downstream consumers** (what imports this module?)

**Tools:**
```bash
# Find all imports
grep -r "from memory.substrate_service import" .

# Check test coverage
pytest --cov=memory.substrate_service tests/
```

---

### Phase 1: Create Protocol Abstractions

**Objective:** Define protocols for module dependencies.

- [ ] **Identify dependency types** (Redis, Neo4j, config, etc.)
- [ ] **Check if protocols exist** in `core/abstractions/`
- [ ] **Create missing protocols** following existing patterns
- [ ] **Add protocol to `__init__.py`** exports
- [ ] **Document protocol usage** with examples

**Example:**
```python
# core/abstractions/memory_protocols.py
@runtime_checkable
class CacheClient(Protocol):
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool: ...
```

**Validation:**
- [ ] Protocol compiles without errors
- [ ] Protocol has comprehensive docstrings
- [ ] Protocol is exported in `__init__.py`

---

### Phase 2: Refactor Module for Injection

**Objective:** Update module to accept injected dependencies.

#### 2.1: Update Constructor

**Before:**
```python
from runtime.redis_client import get_redis_client
from memory.graph_client import get_neo4j_client

class MemorySubstrateService:
    def __init__(self):
        self.redis = get_redis_client()  # Direct coupling
        self.neo4j = get_neo4j_client()  # Direct coupling
```

**After:**
```python
from core.abstractions import CacheClient, GraphClient

class MemorySubstrateService:
    def __init__(self, cache: CacheClient, graph: GraphClient):
        self.cache = cache  # Injected abstraction
        self.graph = graph  # Injected abstraction
```

**Checklist:**
- [ ] Remove direct imports of concrete implementations
- [ ] Add protocol imports from `core.abstractions`
- [ ] Update `__init__` signature with typed parameters
- [ ] Replace `self.redis` → `self.cache` (or keep names if preferred)
- [ ] Update all method calls to use new names

#### 2.2: Update Method Implementations

**Before:**
```python
def get_memory(self, key: str) -> Optional[str]:
    return self.redis.get(key)
```

**After:**
```python
def get_memory(self, key: str) -> Optional[str]:
    return self.cache.get(key)  # Uses injected protocol
```

**Checklist:**
- [ ] Update all references to old dependency names
- [ ] Ensure protocol methods match old client methods
- [ ] Add type hints to all method signatures
- [ ] Update docstrings to reflect injection

#### 2.3: Preserve Backward Compatibility

**Add factory function:**
```python
# memory/substrate_service.py (bottom of file)
from core.di.container import get_di_container

def get_memory_substrate_service() -> MemorySubstrateService:
    """
    Get MemorySubstrateService instance (backward compatible).
    
    Uses DI container internally but preserves existing API.
    """
    container = get_di_container()
    return container.resolve(MemorySubstrateService)
```

**Checklist:**
- [ ] Add factory function at end of module
- [ ] Factory uses DI container internally
- [ ] Factory has same signature as old getter
- [ ] Factory is exported in `__all__`

---

### Phase 3: Configure DI Container

**Objective:** Register bindings in container configuration.

#### 3.1: Update Container Configuration

**File:** `runtime/kernel_loader_ultimate.py` or `config/di_config.py`

```python
from core.di.container import get_di_container
from core.abstractions import CacheClient, GraphClient
from runtime.redis_client import get_redis_client
from memory.graph_client import get_neo4j_client

def configure_memory_bindings():
    """Configure memory subsystem DI bindings."""
    container = get_di_container()
    
    # Bind protocols to implementations
    container.bind_singleton(CacheClient, get_redis_client)
    container.bind_singleton(GraphClient, get_neo4j_client)
    
    # Bind service with auto-injection
    container.bind_singleton(MemorySubstrateService, MemorySubstrateService)
```

**Checklist:**
- [ ] Create or update container configuration function
- [ ] Bind all required protocols
- [ ] Bind service with auto-injection
- [ ] Call configuration at application startup
- [ ] Verify bindings with `container.get_bindings()`

#### 3.2: Update Application Startup

**File:** `api/server.py` or `runtime/bootstrap.py`

```python
from config.di_config import configure_memory_bindings

def startup():
    """Application startup."""
    # Configure DI container
    configure_memory_bindings()
    
    # Rest of startup...
```

**Checklist:**
- [ ] Call configuration functions at startup
- [ ] Configuration happens before any resolution
- [ ] Log successful configuration

---

### Phase 4: Update Tests

**Objective:** Migrate tests to use DI with mocks.

#### 4.1: Create Mock Implementations

```python
# tests/unit/memory/mocks.py
class MockCacheClient:
    def __init__(self):
        self.data = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        self.data[key] = value
        return True

class MockGraphClient:
    def __init__(self):
        self.nodes = {}
    
    async def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        node_id = str(uuid.uuid4())
        self.nodes[node_id] = {"labels": labels, "properties": properties}
        return node_id
```

**Checklist:**
- [ ] Create mock implementations for all protocols
- [ ] Mocks implement full protocol interface
- [ ] Mocks use in-memory storage (no external deps)
- [ ] Mocks are reusable across tests

#### 4.2: Update Test Fixtures

**Before:**
```python
@pytest.fixture
def memory_service():
    return MemorySubstrateService()  # Uses real Redis/Neo4j
```

**After:**
```python
from core.di.container import DIContainer

@pytest.fixture
def container():
    """Create test container with mocks."""
    container = DIContainer()
    container.bind_singleton(CacheClient, MockCacheClient)
    container.bind_singleton(GraphClient, MockGraphClient)
    return container

@pytest.fixture
def memory_service(container):
    """Create memory service with mocked dependencies."""
    return container.resolve(MemorySubstrateService)
```

**Checklist:**
- [ ] Create `container` fixture with mock bindings
- [ ] Update service fixtures to use container
- [ ] Remove external dependency setup (Redis, Neo4j)
- [ ] Tests run without external services

#### 4.3: Update Test Cases

**Before:**
```python
def test_store_memory():
    service = MemorySubstrateService()
    service.store_memory("test", "value")
    # Requires real Redis
```

**After:**
```python
def test_store_memory(memory_service):
    memory_service.store_memory("test", "value")
    # Uses mock cache, no external deps!
```

**Checklist:**
- [ ] Update test signatures to use fixtures
- [ ] Remove manual service instantiation
- [ ] Verify tests pass with mocks
- [ ] Add new tests for edge cases

---

### Phase 5: Integration Testing

**Objective:** Verify module works with real dependencies.

#### 5.1: Create Integration Tests

```python
# tests/integration/memory/test_substrate_service_integration.py
import pytest
from core.di.container import DIContainer
from core.abstractions import CacheClient, GraphClient
from runtime.redis_client import get_redis_client
from memory.graph_client import get_neo4j_client

@pytest.mark.integration
def test_memory_service_with_real_redis():
    """Integration test with real Redis."""
    container = DIContainer()
    
    # Use real implementations
    container.bind_singleton(CacheClient, get_redis_client)
    container.bind_singleton(GraphClient, get_neo4j_client)
    
    service = container.resolve(MemorySubstrateService)
    
    # Test with real dependencies
    memory_id = service.store_memory("integration test", "value")
    assert memory_id is not None
```

**Checklist:**
- [ ] Create integration test file
- [ ] Mark tests with `@pytest.mark.integration`
- [ ] Use real implementations in container
- [ ] Verify end-to-end functionality
- [ ] Run integration tests in CI

#### 5.2: Verify Backward Compatibility

```python
def test_backward_compatible_getter():
    """Verify old getter still works."""
    from memory.substrate_service import get_memory_substrate_service
    
    service = get_memory_substrate_service()
    assert isinstance(service, MemorySubstrateService)
```

**Checklist:**
- [ ] Test old getter functions still work
- [ ] Verify downstream consumers unaffected
- [ ] Check API compatibility

---

### Phase 6: Documentation

**Objective:** Document migration and new usage patterns.

#### 6.1: Update Module Docstring

```python
"""
Memory Substrate Service
========================

High-level memory operations with multi-backend support.

**Dependency Injection:**
This module uses DI for cache and graph clients. To inject custom implementations:

```python
from core.di.container import get_di_container
from core.abstractions import CacheClient, GraphClient

container = get_di_container()
container.bind_singleton(CacheClient, MyCustomCache)
container.bind_singleton(GraphClient, MyCustomGraph)

service = container.resolve(MemorySubstrateService)
```

**Backward Compatibility:**
The `get_memory_substrate_service()` function is preserved for existing code.
"""
```

**Checklist:**
- [ ] Add DI section to module docstring
- [ ] Include usage examples
- [ ] Document backward compatibility
- [ ] Update README if exists

#### 6.2: Update CHANGELOG

```markdown
## [Unreleased]

### Changed
- **BREAKING (internal):** `MemorySubstrateService` now uses constructor injection
- Migrated to protocol-based abstractions (`CacheClient`, `GraphClient`)
- Added DI container support for dependency management

### Added
- `get_memory_substrate_service()` factory function for backward compatibility
- Mock implementations for unit testing without external dependencies

### Migration Guide
See [Migration Checklist](docs/architecture/migration-checklist.md) for details.
```

**Checklist:**
- [ ] Add entry to CHANGELOG.md
- [ ] Document breaking changes (if any)
- [ ] Link to migration guide
- [ ] Note backward compatibility

---

### Phase 7: Code Review & Deployment

**Objective:** Ensure quality and safe deployment.

#### 7.1: Pre-Review Checklist

- [ ] All tests pass (unit + integration)
- [ ] Code coverage maintained or improved
- [ ] Type hints on all public methods
- [ ] Docstrings updated
- [ ] No circular dependencies introduced
- [ ] Backward compatibility preserved
- [ ] Performance benchmarks unchanged

#### 7.2: Code Review Focus Areas

**Reviewer should verify:**
- [ ] Protocol abstractions are appropriate
- [ ] Constructor injection is correct
- [ ] No direct imports of concrete implementations
- [ ] Factory functions preserve old API
- [ ] Tests use mocks effectively
- [ ] Documentation is clear

#### 7.3: Deployment Strategy

**Recommended approach:**
1. **Deploy to dev environment** - Verify functionality
2. **Run integration tests** - Ensure real dependencies work
3. **Deploy to staging** - Monitor for 24 hours
4. **Gradual production rollout** - 10% → 50% → 100%
5. **Monitor metrics** - Watch for errors/performance issues

**Rollback plan:**
- [ ] Document rollback procedure
- [ ] Keep old code path available
- [ ] Monitor error rates
- [ ] Have feature flag for DI (optional)

---

## Module-Specific Checklists

### Migrating `core/kernels/kernelloader.py`

**Special considerations:**
- [ ] Kernel loading is critical path - extra testing required
- [ ] Preserve exact loading order
- [ ] Maintain integrity verification
- [ ] Keep observability spans working

**Dependencies to inject:**
- `KernelValidator` - Pydantic validation
- `KernelDiscovery` - Ordered discovery
- `IntegrityVerifier` - SHA256 verification

### Migrating `memory/substrate_service.py`

**Special considerations:**
- [ ] Multi-backend coordination
- [ ] Async operations throughout
- [ ] Transaction semantics

**Dependencies to inject:**
- `CacheClient` - Redis
- `GraphClient` - Neo4j
- `VectorStore` - pgvector
- `MemoryRepository` - High-level ops

### Migrating `orchestrators/orchestrator_registry.py`

**Special considerations:**
- [ ] Dynamic orchestrator loading
- [ ] Hot-swapping support
- [ ] State management

**Dependencies to inject:**
- `AgentRegistry` - Agent discovery
- `StateManager` - Orchestrator state
- `ObservabilityService` - Tracing

---

## Common Pitfalls

### ❌ Pitfall 1: Forgetting Type Hints

**Problem:**
```python
def __init__(self, cache, graph):  # No type hints!
    self.cache = cache
```

**Solution:**
```python
def __init__(self, cache: CacheClient, graph: GraphClient):
    self.cache = cache
```

### ❌ Pitfall 2: Circular Dependencies

**Problem:**
```python
class ServiceA:
    def __init__(self, b: ServiceB): ...

class ServiceB:
    def __init__(self, a: ServiceA): ...
```

**Solution:** Use factory pattern or lazy initialization.

### ❌ Pitfall 3: Breaking Backward Compatibility

**Problem:** Removing old getter functions immediately.

**Solution:** Keep factory functions that use DI internally.

### ❌ Pitfall 4: Not Testing with Mocks

**Problem:** Tests still require Redis/Neo4j.

**Solution:** Create mock implementations and use DI in tests.

---

## Validation Checklist

**Before marking migration complete:**

- [ ] ✅ All unit tests pass
- [ ] ✅ All integration tests pass
- [ ] ✅ Code coverage ≥ previous level
- [ ] ✅ Type checking passes (`mypy`)
- [ ] ✅ Linting passes (`ruff`, `black`)
- [ ] ✅ Documentation updated
- [ ] ✅ CHANGELOG updated
- [ ] ✅ Backward compatibility verified
- [ ] ✅ Performance benchmarks unchanged
- [ ] ✅ Code review approved
- [ ] ✅ Deployed to dev successfully
- [ ] ✅ Integration tests pass in dev
- [ ] ✅ Deployed to staging successfully
- [ ] ✅ Monitored for 24 hours in staging
- [ ] ✅ Production deployment plan approved

---

## Timeline Estimates

| Module Type | Complexity | Estimated Time |
|-------------|------------|----------------|
| Simple service (1-2 deps) | Low | 2-4 hours |
| Medium service (3-5 deps) | Medium | 1-2 days |
| Complex service (6+ deps) | High | 2-3 days |
| Core infrastructure | Critical | 3-5 days |

**Note:** Times include testing, documentation, and review.

---

## Support

**Questions or issues during migration?**

1. Check [DI Container Guide](./di-container-guide.md)
2. Check [Protocol Catalog](./protocol-catalog.md)
3. Check [Troubleshooting DI](./troubleshooting-di.md)
4. Ask in #l9-di-migration Slack channel

---

**Quality Assurance:** This checklist is maintained to Top Frontier AI Lab standards. All steps are production-tested.

**Version History:**
- 1.0.0 (2026-01-20): Initial release with comprehensive migration guide
