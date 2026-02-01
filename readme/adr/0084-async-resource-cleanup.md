# ADR-0084: Async Resource Cleanup Pattern

**Status:** Accepted  
**Date:** 2026-01-31  
**Source:** Bug Audit PR #83  

## Context

HTTP clients like `httpx.AsyncClient` hold resources (connections, file handles) that must be explicitly closed. Manual `.aclose()` calls are error-prone and can be forgotten in error paths.

## Decision

**All async HTTP clients MUST use async context managers for automatic cleanup.**

### Forbidden Pattern

```python
# BAD - resource leak if exception before aclose()
client = httpx.AsyncClient()
response = await client.get(url)
await client.aclose()  # May never execute!
```

### Required Pattern

```python
# GOOD - guaranteed cleanup via context manager
async with httpx.AsyncClient() as client:
    response = await client.get(url)
    # Client auto-closed on exit (even on exception)
```

## Enforcement

- **Semgrep rule:** `l9-httpx-async-context-required` in `.semgrep/l9-rules.yaml`
- **CI gate:** Fails build on violation
- **Scope:** `api/`, `core/`, `services/`

## Approved Exceptions (False Positives)

The semgrep rule cannot detect these valid patterns. Use `# nosemgrep: l9-httpx-async-context-required` with explanation:

| Pattern | Example | Why Allowed |
|---------|---------|-------------|
| **Lifecycle clients** | `app.state.http_client` | Stored in app state, closed in `@app.on_event("shutdown")` |
| **Context manager impl** | `__aenter__` creating client | Closed by corresponding `__aexit__` |
| **try/finally** | `http_client = httpx.AsyncClient()` with `finally: await http_client.aclose()` | Explicit cleanup in finally |
| **Fallback with close()** | Lazy init with documented `close()` method | Manual cleanup available |

### Suppression Format

```python
# nosemgrep: l9-httpx-async-context-required (reason here)
http_client = httpx.AsyncClient()
```

### Current Approved Locations

| File | Line | Reason |
|------|------|--------|
| `api/server.py` | ~1573 | Lifecycle client, shutdown at L2800 |
| `api/server_memory.py` | ~207 | Lifecycle client, shutdown handler |
| `api/slack_client.py` | ~362 | try/finally cleanup |
| `services/research/tools/perplexity_client.py` | ~187 | Context manager `__aenter__` |
| `services/research/tools/perplexity_client.py` | ~249 | Fallback with `close()` method |
| `services/slack_files.py` | ~689 | try/finally at L705 |

## Consequences

- No resource leaks from HTTP clients
- Cleaner code with guaranteed cleanup
- Proper cleanup even in error paths
