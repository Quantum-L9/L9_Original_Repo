# ADR 0043: Security & Rate Limiting Architecture

**Date**: 2026-01-23

**Status**: Accepted

**Supersedes**: PR #36 (fix/security-eval-and-rate-limiting)

## Context

The L9 platform requires protection against:

1. **Code injection** via `eval()`, `exec()`, `__import__()`
2. **API abuse** via missing rate limiting
3. **Brute force attacks** on authentication endpoints
4. **Resource exhaustion** from uncontrolled requests

Analysis of PR #36 revealed these protections were already implemented across multiple modules, but undocumented. This ADR consolidates the security architecture for AI and human reviewers.

## Decision

We maintain a **defense-in-depth** approach with multiple security layers:

### 1. Rate Limiting Architecture

| Layer              | File                               | Purpose                    | Algorithm          |
| ------------------ | ---------------------------------- | -------------------------- | ------------------ |
| **General API**    | `runtime/rate_limiter.py`          | Per-endpoint rate limiting | Sliding window     |
| **Authentication** | `runtime/auth_rate_limiter.py`     | Brute force prevention     | IP + user tracking |
| **MCP Memory**     | `mcp_memory/src/rate_limiter.py`   | Memory server protection   | Versioned buckets  |
| **Tool Registry**  | `core/tools/base_registry.py`      | Per-tool rate limits       | Sliding window     |
| **Policy Config**  | `config/policies/rate_limits.yaml` | Centralized limits         | YAML config        |

### 2. Code Injection Prevention

| Risk                           | Mitigation                 | Location                              |
| ------------------------------ | -------------------------- | ------------------------------------- |
| `eval()` in expressions        | AST-based safe evaluator   | `core/tools/base_registry.py:557-602` |
| `eval()` in DI container       | `typing.get_type_hints()`  | `core/di/container.py:337-354`        |
| `eval()`/`exec()` in code exec | Forbidden pattern blocking | `runtime/execution_gate.py:127-131`   |
| `__import__()` dynamic imports | Direct static imports      | All modules (enforced)                |

### 3. Execution Gate (Defense Layer)

The `runtime/execution_gate.py` provides a final safety net that blocks dangerous patterns:

```python
FORBIDDEN_PATTERNS = {
    "code": [
        "eval(",
        "exec(",
        "__import__",
        "open(",
        "os.system",
        # ... more patterns
    ]
}
```

## Implementation Details

### Rate Limiter: `runtime/rate_limiter.py`

**Purpose**: General-purpose sliding window rate limiter with Redis backend.

**Key Features**:

- Redis backend with automatic in-memory fallback
- Sliding window algorithm (configurable window size)
- Neo4j audit logging for rate limit events
- Async-safe operations

**Usage**:

```python
from runtime.rate_limiter import RateLimiter

limiter = RateLimiter(window_seconds=60)

# Check and increment
if await limiter.check_and_increment("endpoint:chat", limit=100):
    # Request allowed
else:
    # Rate limited
```

**Integration Points**:

- `api/server.py` - API endpoint protection
- `core/tools/base_registry.py` - Tool execution limits

---

### Auth Rate Limiter: `runtime/auth_rate_limiter.py`

**Purpose**: OWASP-compliant authentication rate limiting.

**Key Features**:

- Per-IP, per-user, and combined tracking
- Automatic lockout after N failures (default: 5)
- Progressive delays on failures (exponential backoff)
- Configurable lockout duration (default: 15 minutes)
- Success clears user failure count

**Usage**:

```python
from runtime.auth_rate_limiter import get_auth_rate_limiter

limiter = get_auth_rate_limiter()

# Before auth attempt
result = await limiter.check_allowed(ip_address, username)
if not result.allowed:
    raise HTTPException(429, result.reason)

# After failed attempt
await limiter.record_failure(ip_address, username)

# After success
await limiter.record_success(ip_address, username)
```

**Integration Points**:

- `api/auth.py` - Authentication endpoints
- `api/dependencies.py` - FastAPI dependency injection

---

### MCP Rate Limiter: `mcp_memory/src/rate_limiter.py`

**Purpose**: Memory server-specific rate limiting with versioned buckets.

**Key Features**:

- Async-safe with lock protection
- Version tracking for concurrency detection
- Separate request and auth failure tracking
- Immutable snapshots for auditing

**Usage**:

```python
from mcp_memory.src.rate_limiter import RateLimiter

limiter = RateLimiter(
    request_limit=100,
    request_window_seconds=60,
    failed_auth_limit=5,
    failed_auth_block_seconds=900
)

if await limiter.is_rate_limited(ip):
    # Block request
```

---

### Safe Expression Evaluator: `core/tools/base_registry.py`

**Purpose**: Calculator tool that safely evaluates mathematical expressions.

**Key Features**:

- Uses `ast.parse()` + custom walker (NOT `eval()`)
- Whitelist of allowed operations: `+`, `-`, `*`, `/`, `**`, unary `-`
- Limited builtin functions: `abs`, `round`, `min`, `max`
- Clear error messages for invalid expressions

**Implementation** (lines 557-602):

```python
def calculate_executor(expression: str) -> dict:
    import ast
    import operator

    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_expr(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operation")
            return op(eval_expr(node.left), eval_expr(node.right))
        # ... more node types

    tree = ast.parse(expression, mode='eval')
    result = eval_expr(tree.body)
    return {"result": result}
```

---

### DI Container Type Resolution: `core/di/container.py`

**Purpose**: Safe resolution of string type annotations without `eval()`.

**Key Features**:

- Uses `typing.get_type_hints()` instead of `eval()`
- Handles forward references safely
- Falls back gracefully on resolution failure

**Implementation** (lines 337-354):

```python
if isinstance(annotation, str):
    try:
        from typing import get_type_hints
        if inspect.isclass(factory):
            hints = get_type_hints(factory.__init__, globalns=factory.__init__.__globals__)
            annotation = hints.get(param.name, annotation)
        else:
            hints = get_type_hints(factory, globalns=factory.__globals__)
            annotation = hints.get(param.name, annotation)
    except Exception:
        # Skip unresolvable annotations
        continue
```

---

### Execution Gate: `runtime/execution_gate.py`

**Purpose**: Final safety layer blocking dangerous code patterns.

**Key Features**:

- Pattern-based blocking for dangerous operations
- Whitelist approach for allowed operations
- Audit logging of blocked attempts

**Forbidden Patterns**:

```python
FORBIDDEN_PATTERNS = {
    "code": ["eval(", "exec(", "__import__", "open(", "os.system", ...],
    "shell": ["rm -rf", "sudo", "chmod 777", ...],
    "file": ["/etc/passwd", "/etc/shadow", "~/.ssh", ...],
}
```

## Configuration

### Rate Limit Policy: `config/policies/rate_limits.yaml`

Centralized configuration for rate limits:

```yaml
default:
  requests_per_minute: 60
  burst_size: 10

endpoints:
  /api/chat:
    requests_per_minute: 30
    burst_size: 5
  /api/memory/ingest:
    requests_per_minute: 100
    burst_size: 20

auth:
  max_failures_per_ip: 10
  max_failures_per_user: 5
  lockout_duration_seconds: 900
```

## Consequences

### Positive

- **Defense in depth**: Multiple layers prevent single-point failures
- **Performance**: Redis backend for distributed rate limiting
- **Observability**: Neo4j audit logging for security events
- **Flexibility**: Configurable via YAML without code changes
- **OWASP compliance**: Auth rate limiting follows best practices

### Negative

- **Complexity**: Multiple rate limiters to maintain
- **Learning curve**: New developers must understand all layers

### Neutral

- Existing implementations supersede PR #36 approach
- No breaking changes to existing APIs

## File Index

### Core Security Files

| File                             | Lines | Purpose                     |
| -------------------------------- | ----- | --------------------------- |
| `runtime/rate_limiter.py`        | 380   | General rate limiting       |
| `runtime/auth_rate_limiter.py`   | 505   | Auth-specific rate limiting |
| `runtime/execution_gate.py`      | ~400  | Code execution safety       |
| `core/tools/base_registry.py`    | 1327  | Safe expression evaluation  |
| `core/di/container.py`           | 577   | Safe type resolution        |
| `mcp_memory/src/rate_limiter.py` | 207   | MCP rate limiting           |

### Configuration Files

| File                                   | Purpose             |
| -------------------------------------- | ------------------- |
| `config/policies/rate_limits.yaml`     | Rate limit settings |
| `core/governance/rate_limit_policy.py` | Policy enforcement  |

### Test Files

| File                                                 | Purpose                |
| ---------------------------------------------------- | ---------------------- |
| `tests/runtime/test_execution_gate.py`               | Execution gate tests   |
| `tests/orchestrators/test_rate_limit_persistence.py` | Rate limit tests       |
| `mcp_memory/tests/test_rate_limiter.py`              | MCP rate limiter tests |
| `mcp_memory/tests/test_rate_limiting_enforcement.py` | Enforcement tests      |

## Related

- PR #36: Superseded by existing implementations
- ADR 0019: Structlog logging standard (includes security logging)
- `SECURITY.md`: Public security policy

## DORA Metadata

```yaml
component_id: ADR-0043
governance_level: high
compliance_required: true
audit_trail: true
dependencies:
  - runtime.rate_limiter
  - runtime.auth_rate_limiter
  - runtime.execution_gate
  - core.tools.base_registry
  - core.di.container
tags:
  - adr
  - security
  - rate-limiting
  - code-injection
  - defense-in-depth
business_value: Documents L9's security architecture for code reviewers and AI systems
last_modified: "2026-01-23T22:00:00Z"
modified_by: "Igor"
```
