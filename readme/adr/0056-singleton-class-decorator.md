# ADR-0056: Singleton Class Decorator Pattern

## Status
Accepted (Implemented in PR #53)

## Context
L9 has multiple service classes that should only have a single instance throughout the application lifecycle (e.g., `ExecutorToolRegistry`, `EventQueue`). While ADR-0004 covers singleton service registration via `@register_singleton`, we needed a general-purpose class-level singleton decorator for non-service classes.

**Problems with manual singleton implementation**:
1. Boilerplate code repeated across multiple classes
2. Thread-safety concerns in async environment
3. Inconsistent singleton patterns across codebase
4. Manual instance management prone to errors

## Decision
Implement a thread-safe `@singleton` class decorator that:
1. Ensures only one instance of a class exists
2. Thread-safe initialization using `threading.Lock`
3. Works with any class (not just services)
4. Transparent to class consumers (no API changes)

## Implementation

### Decorator Location
`core/patterns/singleton.py`

### Usage
```python
from core/patterns.singleton import singleton

@singleton
class ExecutorToolRegistry:
    def __init__(self):
        self._registry = {}
    
    def register(self, tool_id, tool):
        self._registry[tool_id] = tool

# Usage - always returns same instance
registry1 = ExecutorToolRegistry()
registry2 = ExecutorToolRegistry()
assert registry1 is registry2  # True
```

### Classes Using @singleton
- `core/tools/registry_adapter.py::ExecutorToolRegistry`
- `core/coordination/event_queue.py::EventQueue`

## Consequences

### Positive
- **Consistency**: All singletons use same pattern
- **Thread-safety**: No race conditions in async environment
- **Simplicity**: One-line decorator vs 10+ lines of boilerplate
- **Transparency**: No changes to class consumers
- **Testability**: Can reset instances in tests if needed

### Negative
- **Global state**: Singletons are global, can complicate testing
- **Hidden dependencies**: Singleton usage not obvious from function signatures
- **Lifecycle management**: Harder to control initialization order

### Neutral
- **Coexists with ADR-0004**: `@register_singleton` for services, `@singleton` for utility classes

## Alternatives Considered

### 1. Module-level instances
```python
# registry.py
_registry = ExecutorToolRegistry()

def get_registry():
    return _registry
```
**Rejected**: Not thread-safe, no lazy initialization

### 2. Metaclass-based singleton
```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class MyClass(metaclass=SingletonMeta):
    pass
```
**Rejected**: More complex, harder to understand, conflicts with other metaclasses

### 3. Dependency injection container
```python
container.register_singleton(ExecutorToolRegistry)
registry = container.resolve(ExecutorToolRegistry)
```
**Rejected**: Overkill for current needs, adds complexity

## Relationship to Other ADRs
- **ADR-0004 (Singleton Auto-Registry)**: Complementary - ADR-0004 for services, ADR-0056 for utility classes
- **ADR-0052 (DI/DIP Foundation)**: Future - may migrate to DI container later

## Migration Path
1. ✅ **Phase 1** (PR #53): Create decorator, apply to 2 classes
2. **Phase 2** (Future): Audit codebase for manual singleton patterns
3. **Phase 3** (Future): Migrate manual singletons to `@singleton`

## Verification
```bash
# Test singleton behavior
python3 -c "
from core.tools.registry_adapter import ExecutorToolRegistry
r1 = ExecutorToolRegistry()
r2 = ExecutorToolRegistry()
assert r1 is r2, 'Singleton failed'
print('✅ Singleton working')
"
```

## References
- PR #53: Design Pattern Improvements
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md`
- Gang of Four: Singleton Pattern

## Notes
- Thread-safe via `threading.Lock` (not `asyncio.Lock`) because class instantiation is synchronous
- Decorator stores instances in `_instances` dict on function object
- Works with `__init__` parameters (passes through to class)

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**GMP**: design-patterns-pr53
