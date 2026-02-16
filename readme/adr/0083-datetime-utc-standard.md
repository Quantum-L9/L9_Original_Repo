# ADR-0083: Datetime UTC Standard

**Status:** Accepted
**Date:** 2026-01-31
**Source:** Bug Audit PR #81

## Context

Python's `datetime.utcnow()` is deprecated as of Python 3.12. It returns a naive datetime object without timezone information, which can lead to subtle bugs when comparing timestamps across systems.

## Decision

**All datetime creation MUST use `datetime.now(UTC)` instead of `datetime.utcnow()`.**

### Forbidden Pattern

```python
# BAD - deprecated, returns naive datetime
timestamp = datetime.utcnow()
```

### Required Pattern

```python
# GOOD - returns timezone-aware datetime
from datetime import UTC, datetime

timestamp = datetime.now(UTC)
```

## Enforcement

- **Semgrep rule:** `l9-no-datetime-utcnow` in `.semgrep/l9-rules.yaml`
- **CI gate:** Fails build on violation
- **Scope:** `api/`, `core/`, `runtime/`, `services/`, `agents/`, `memory/`

## Consequences

- All timestamps are timezone-aware
- Consistent timestamp handling across services
- Forward-compatible with Python 3.12+
