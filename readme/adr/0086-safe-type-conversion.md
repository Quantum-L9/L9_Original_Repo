# ADR-0086: Safe Type Conversion Pattern

**Status:** Accepted  
**Date:** 2026-01-31  
**Source:** Bug Audit PR #83  

## Context

Type conversion functions like `float()`, `int()`, `json.loads()` raise exceptions on invalid input. Unhandled exceptions in production code can crash request handlers.

## Decision

**Type conversions on untrusted input MUST use try/except with explicit fallback.**

### Forbidden Pattern

```python
# BAD - crashes on invalid input
value = float(user_input)  # ValueError: could not convert string to float: 'abc'
```

### Required Pattern

```python
# GOOD - graceful handling with fallback
try:
    value = float(user_input)
except (ValueError, TypeError):
    value = default_value  # Explicit fallback
    logger.warning(f"Invalid float input: {user_input}")
```

### When Exception is Preferred

```python
# OK - when validation is the intent
def parse_required_float(value: str) -> float:
    """Parse float or raise descriptive error."""
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Expected float, got: {value}") from e
```

## Enforcement

- **Semgrep rule:** `l9-float-requires-try-except` in `.semgrep/l9-rules.yaml`
- **CI gate:** Warning (manual review for false positives)
- **Scope:** `api/`, `core/`

## False Positives (No Action Needed)

The semgrep rule is intentionally broad. These patterns are **safe** and do NOT need try/except:

| Pattern | Why Safe |
|---------|----------|
| `float(tensor.item())` | Torch tensors always contain numeric values |
| `float(np.mean(...))` | NumPy operations return numeric types |
| `float(value)` after `isinstance(value, (int, float))` | Type already validated |
| `float(os.getenv("X", "0.75"))` | Default is valid float literal |
| `return float(computed_result)` | Internal computation, not user input |

**When to add `# nosemgrep:`:**
- Only for high-traffic code paths where the warning is noisy
- Prefer leaving warnings for audit trail

## Consequences

- No crashes from invalid input
- Explicit handling of edge cases
- Better error messages for debugging
