# ADR-0057: Decorator Metadata Preservation with functools.wraps

## Status
Accepted (Implemented in PR #53)

## Context
L9 uses decorators extensively for cross-cutting concerns (retry, rate limiting, logging, caching, etc.). However, many decorators were missing `@functools.wraps`, causing loss of function metadata (`__name__`, `__doc__`, `__module__`, `__annotations__`).

**Problems without @wraps**:
1. **Debugging**: Stack traces show `wrapper` instead of actual function name
2. **Introspection**: `help()` and `inspect` show wrong function signature
3. **Documentation**: Docstrings lost after decoration
4. **Type hints**: Annotations lost, breaking type checkers
5. **Testing**: Mocks and patches fail due to wrong function names

**Audit findings**:
- 105 decorator definitions in codebase
- Only 2 used `@functools.wraps` consistently
- 5 decorators identified as critical to fix immediately

## Decision
**MANDATE** that all decorators in L9 MUST use `@functools.wraps(func)` to preserve function metadata.

Create `core/decorators_enhanced.py` with 8 production-ready decorators that:
1. Use `@functools.wraps` correctly
2. Support both sync and async functions
3. Follow consistent patterns
4. Include comprehensive docstrings

## Implementation

### Enhanced Decorators Library
`core/decorators_enhanced.py` (600+ lines)

**Decorators provided**:
1. `async_retry` - Exponential backoff retry for async functions
2. `rate_limit` - Rate limiting with token bucket algorithm
3. `log_execution` - Automatic execution logging
4. `cache_result` - In-memory caching with TTL
5. `measure_performance` - Performance metrics collection
6. `timeout` - Async timeout enforcement
7. `sync_retry` - Retry for sync functions
8. `sync_log_execution` - Logging for sync functions

### Fixed Decorators
- `core/instrumentation/decorators.py::with_source_location` - Added `@wraps`
- 4 other decorators (see PR #53 for full list)

### Standard Pattern
```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # ← REQUIRED
    async def async_wrapper(*args, **kwargs):
        # Pre-processing
        result = await func(*args, **kwargs)
        # Post-processing
        return result
    
    @wraps(func)  # ← REQUIRED
    def sync_wrapper(*args, **kwargs):
        # Pre-processing
        result = func(*args, **kwargs)
        # Post-processing
        return result
    
    # Return appropriate wrapper
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
```

## Consequences

### Positive
- **Better debugging**: Stack traces show actual function names
- **Type safety**: Type checkers work correctly
- **Documentation**: `help()` shows correct docstrings
- **Introspection**: `inspect.signature()` returns correct signature
- **Testing**: Mocks and patches work as expected
- **Consistency**: All decorators follow same pattern

### Negative
- **Slight overhead**: `@wraps` adds minimal runtime cost (negligible)
- **Migration effort**: Need to audit and fix existing decorators

### Neutral
- **Standard practice**: Following Python best practices

## Rules

### HARD RULES
1. **ALL decorators MUST use `@functools.wraps(func)`**
2. **NO exceptions** - even simple decorators need `@wraps`
3. **CI enforcement** - Anti-pattern test catches violations

### Decorator Checklist
- [ ] Import `from functools import wraps`
- [ ] Apply `@wraps(func)` to wrapper function
- [ ] Support both sync and async if applicable
- [ ] Include docstring with usage example
- [ ] Test that `__name__` and `__doc__` are preserved

## Examples

### ❌ BAD (No @wraps)
```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def my_function():
    """My docstring"""
    pass

print(my_function.__name__)  # "wrapper" ❌
print(my_function.__doc__)   # None ❌
```

### ✅ GOOD (With @wraps)
```python
from functools import wraps

def log_calls(func):
    @wraps(func)  # ← REQUIRED
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def my_function():
    """My docstring"""
    pass

print(my_function.__name__)  # "my_function" ✅
print(my_function.__doc__)   # "My docstring" ✅
```

## Verification

### Anti-Pattern Test
`tests/ci/test_anti_patterns.py::test_decorator_functools_wraps`

Scans codebase for decorators missing `@wraps` and fails CI if found.

### Manual Check
```bash
# Check decorator metadata preservation
python3 -c "
from core.decorators_enhanced import async_retry

@async_retry(max_retries=3)
async def my_func():
    '''My docstring'''
    pass

assert my_func.__name__ == 'my_func'
assert 'My docstring' in my_func.__doc__
print('✅ Metadata preserved')
"
```

## Alternatives Considered

### 1. Manual metadata copying
```python
def decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    # ... copy all attributes manually
    return wrapper
```
**Rejected**: Error-prone, incomplete, reinventing the wheel

### 2. No metadata preservation
**Rejected**: Breaks debugging, introspection, type checking

### 3. Custom @wraps alternative
**Rejected**: Unnecessary complexity, `functools.wraps` is standard

## Relationship to Other ADRs
- **ADR-0010 (Must Stay Async Decorator)**: Enhanced with `@wraps`
- **ADR-0018 (Async Retry Pattern)**: Enhanced with `@wraps`
- **ADR-0019 (Structlog Logging Standard)**: `log_execution` decorator follows this

## Migration Path
1. ✅ **Phase 1** (PR #53): Create `decorators_enhanced.py`, fix 5 critical decorators
2. **Phase 2** (Future): Audit remaining 100+ decorators
3. **Phase 3** (Future): Add CI gate to enforce `@wraps` usage

## References
- Python docs: [`functools.wraps`](https://docs.python.org/3/library/functools.html#functools.wraps)
- PEP 318: Decorators for Functions and Methods
- PR #53: Design Pattern Improvements
- Design Pattern Audit Report: `L9_DESIGN_PATTERN_AUDIT_REPORT.md`

## Notes
- `@wraps` copies: `__module__`, `__name__`, `__qualname__`, `__annotations__`, `__doc__`, `__dict__`
- For class decorators, use `functools.update_wrapper` instead
- `@wraps` is idempotent - safe to apply multiple times

---
**Created**: 2026-01-23  
**Author**: L9 Design Pattern Audit  
**GMP**: design-patterns-pr53
