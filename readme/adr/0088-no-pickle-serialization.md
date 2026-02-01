# ADR-0088: No Pickle Serialization

**Status:** Accepted  
**Date:** 2026-01-31  
**Source:** Bug Audit PR #84 (CRITICAL Security Fix)  

## Context

Python's `pickle` module can execute arbitrary code during deserialization. Loading pickled data from untrusted sources (cache, network, files) is a remote code execution vulnerability.

## Decision

**`pickle.loads()` is FORBIDDEN. Use JSON or other safe serialization formats.**

### Forbidden Pattern

```python
# BAD - arbitrary code execution vulnerability (CRITICAL)
import pickle

cached_data = redis.get(key)
data = pickle.loads(cached_data)  # Could execute malicious code!
```

### Required Pattern

```python
# GOOD - safe JSON serialization
import json

cached_data = redis.get(key)
data = json.loads(cached_data)

# For complex types, use explicit serialization
data = json.loads(cached_data, object_hook=custom_decoder)
```

### Acceptable Alternatives

| Format | Use Case |
|--------|----------|
| `json` | General structured data |
| `msgpack` | Binary efficiency |
| `protobuf` | Schema-enforced messages |
| `pydantic.model_dump_json()` | Pydantic models |

## Enforcement

- **Semgrep rule:** `l9-no-pickle-loads` in `.semgrep/l9-rules.yaml`
- **ADR rule:** ADR-0041 (extended)
- **CI gate:** ERROR - Blocks merge
- **Scope:** All Python files

## Migration

Existing pickle usage must be migrated:

```python
# OLD (vulnerable)
await redis.setex(key, ttl, pickle.dumps(data))
data = pickle.loads(await redis.get(key))

# NEW (safe)
await redis.setex(key, ttl, json.dumps(data, default=str))
data = json.loads(await redis.get(key))
```

## Consequences

- No deserialization vulnerabilities
- Explicit control over what gets deserialized
- Better interoperability (JSON is language-agnostic)
