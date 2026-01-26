# ADR 0055: Fail-Loudly vs Graceful Degradation Policy

## Status

Accepted

## Pattern

Core infrastructure (kernels, memory, execution runtime) MUST fail loudly with `RuntimeError`. Observability layers (metrics, telemetry, Neo4j graph) MAY degrade gracefully.

## Context

L9 had inconsistent error handling — some components failed silently (returning `None`, swallowing exceptions), while others crashed hard. GMP-47 (Stub Elimination) and GMP-75 (Silent Failure Audit) established that silent failures are anti-patterns that hide bugs and make debugging impossible.

This ADR formalizes when each approach is appropriate.

## Decision

### FAIL LOUDLY (RuntimeError) — Required For:

| Component             | Reason                               | Example                                            |
| --------------------- | ------------------------------------ | -------------------------------------------------- |
| **Kernel Loading**    | Agent cannot operate without kernels | `raise RuntimeError("Required kernel missing")`    |
| **AIOS Runtime**      | Execution impossible without runtime | `raise RuntimeError("AIOSRuntime import failed")`  |
| **Tool Registry**     | Agent cannot dispatch tools          | `raise RuntimeError("ToolRegistry unavailable")`   |
| **PostgreSQL**        | Memory, tasks, users require DB      | `raise RuntimeError("Database connection failed")` |
| **Memory Ingestion**  | Audit trail is mandatory             | `raise HTTPException(500, "Ingestion failed")`     |
| **Agent Registry**    | Cannot instantiate agents            | `raise RuntimeError("AgentRegistry failed")`       |
| **Required Env Vars** | Security/config is mandatory         | `raise RuntimeError("OPENAI_API_KEY not set")`     |

### GRACEFUL DEGRADATION — Allowed For:

| Component              | Reason                                 | Fallback Behavior                                  |
| ---------------------- | -------------------------------------- | -------------------------------------------------- |
| **Neo4j Graph**        | Observability layer, not critical path | Log warning, set `app.state.neo4j_healthy = False` |
| **Prometheus Metrics** | Telemetry shouldn't break execution    | Silent no-op, log debug                            |
| **Packet Emission**    | Observability shouldn't block          | Best-effort, continue execution                    |
| **Memory Warming**     | Performance optimization only          | Skip warming, log info                             |
| **Graph Hydration**    | Enhancement, not requirement           | Skip hydration, continue                           |
| **Self-Reflection**    | Analytics, not critical path           | Skip reflection, log debug                         |

## Minimal Implementation

### Fail-Loudly Pattern

```python
def load_required_service():
    """Load a required service — FAIL LOUDLY if unavailable."""
    try:
        service = create_service()
        if service is None:
            raise RuntimeError("Service creation returned None")
        return service
    except ImportError as e:
        raise RuntimeError(f"Required import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Service initialization failed: {e}") from e

# Usage in server startup
if not _has_aios_runtime:
    raise RuntimeError(
        "FATAL: AIOSRuntime import failed. "
        "Server cannot start without execution runtime."
    )
```

### Graceful Degradation Pattern

```python
def init_optional_service():
    """Initialize optional service — graceful degradation if unavailable."""
    try:
        service = create_optional_service()
        logger.info("optional_service.initialized")
        return service
    except ImportError:
        logger.warning("optional_service.unavailable", reason="import_failed")
        return None
    except Exception as e:
        logger.warning("optional_service.failed", error=str(e))
        return None

# Usage with fallback
if optional_service:
    await optional_service.enhance(data)
else:
    logger.debug("optional_service.skipped", reason="not_available")
```

## Anti-Pattern Examples

```python
# ❌ WRONG — Silent failure hides bugs
def get_kernel(kernel_id: str) -> Optional[Dict]:
    try:
        return load_kernel(kernel_id)
    except Exception:
        return None  # BUG: Caller doesn't know why it failed!

# ❌ WRONG — Graceful degradation for critical path
def init_database():
    try:
        return connect_to_postgres()
    except Exception as e:
        logger.warning("Database unavailable, continuing anyway")
        return None  # BUG: System will fail in unpredictable ways later!

# ✅ CORRECT — Fail loudly for critical path
def init_database():
    try:
        db = connect_to_postgres()
        if db is None:
            raise RuntimeError("Database connection returned None")
        return db
    except Exception as e:
        raise RuntimeError(f"FATAL: Database connection failed: {e}") from e

# ✅ CORRECT — Graceful degradation for observability
def init_metrics():
    try:
        return PrometheusMetrics()
    except ImportError:
        logger.info("metrics.disabled", reason="prometheus_client not installed")
        return NoOpMetrics()
```

## Decision Tree

```
Is this component required for agent operation?
│
├─► YES (kernels, runtime, DB, tools)
│   └─► FAIL LOUDLY with RuntimeError
│       - Include clear error message
│       - Include root cause (from e)
│       - Do NOT catch and return None
│
└─► NO (metrics, telemetry, graph queries, warming)
    └─► GRACEFUL DEGRADATION allowed
        - Log warning/info with reason
        - Return None or NoOp implementation
        - Set health flag (e.g., app.state.neo4j_healthy = False)
        - Continue execution
```

## Rules

1. **Critical path = fail loudly** — If agent cannot function without it, raise `RuntimeError`
2. **Observability = graceful degradation** — Metrics/telemetry should never break execution
3. **No silent failures** — Every failure MUST be logged (even graceful ones)
4. **Include root cause** — Use `raise X from e` to preserve stack trace
5. **Clear error messages** — State WHAT failed and WHY
6. **Health flags for degraded state** — Set `app.state.X_healthy = False` when degrading
7. **Never `except: pass`** — This is always wrong

## Validation

### Fail-Loudly Checklist

- [ ] Kernel loading raises `RuntimeError` on missing kernels
- [ ] Database connection raises `RuntimeError` on failure
- [ ] AIOS runtime raises `RuntimeError` if import fails
- [ ] Tool registry raises `RuntimeError` if unavailable
- [ ] Memory ingestion returns HTTP 500 on failure

### Graceful Degradation Checklist

- [ ] Neo4j unavailable → logs warning, sets health flag, continues
- [ ] Prometheus unavailable → silent no-op, doesn't crash
- [ ] Memory warming unavailable → logs info, skips, continues

## AI Guidance

**DO:**

- Raise `RuntimeError` for any component the agent needs to function
- Include clear error messages explaining what failed
- Use `raise X from e` to preserve the exception chain
- Log warnings for graceful degradation (never silent)
- Set health flags when degrading (`app.state.X_healthy = False`)

**DO NOT:**

- Return `None` without logging when a required component fails
- Use `except: pass` or `except Exception: return None` for critical paths
- Allow observability failures to crash the server
- Silently swallow exceptions (always log something)
- Assume "it might work later" — fail fast, fail clearly

## Related ADRs

- [ADR-0023: Error Packet Pattern](./0023-error-packet-pattern.md)
- [ADR-0009: Circuit Breaker Resilience](./0009-circuit-breaker-resilience.md)

## Related GMPs

- **GMP-47**: Stub Elimination — Established fail-loudly for critical stubs
- **GMP-75**: Silent Failure Audit — Fixed 7 silent failures in substrate_service.py
- **GMP-60**: Runtime Hardening — Added kernel integrity verification

## References

- `docs/GRACEFUL_DEGRADATION_VS_FAIL_LOUDLY.md` — Original policy document
- `ci/STRICT_MODE.md` — CI enforcement ("Silent failure - Must emit error packet")
- `.cursor/rules/00-global.mdc` — "Fail loud, fail fast" rule
