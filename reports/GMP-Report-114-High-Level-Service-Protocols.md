# GMP-114: High-Level Service Protocols & ADR Enforcement

**Date:** 2026-01-24
**Tier:** RUNTIME_TIER
**Status:** ✅ COMPLETE
**Source:** PR #49 (ADR Enforcement Infrastructure) — Concepts Extracted

---

## Summary

Adopted useful concepts from PR #49 while avoiding conflicting implementations:

- Added ADR enforcement hooks to pre-commit
- Expanded ruff linting rules for better code quality
- Created high-level service protocols (MemoryService, LLMService, GovernanceService)
- Registered protocols in protocol registry

---

## TODO Plan (Executed)

| T#  | File                                  | Lines        | Action  | Description           | Status |
| --- | ------------------------------------- | ------------ | ------- | --------------------- | ------ |
| T1  | `.pre-commit-config.yaml`             | EOF          | Insert  | ADR enforcement hooks | ✅     |
| T2  | `pyproject.toml`                      | 39-64        | Replace | Expanded ruff rules   | ✅     |
| T3  | `core/protocols/service_protocols.py` | NEW          | Create  | High-level protocols  | ✅     |
| T4  | `core/protocols/__init__.py`          | 46-48, 82-85 | Insert  | Register protocols    | ✅     |

---

## Changes Made

### T1: Pre-commit ADR Hooks

Added two local hooks for ADR enforcement:

```yaml
- id: enforce-structlog (ADR-0019)
  Detects `import logging` and recommends structlog

- id: check-dora-metadata
  Warns if __dora_meta__ missing in Python files
```

### T2: Expanded Ruff Rules

```toml
select = [
    "F",      # Pyflakes
    "E7",     # pycodestyle errors
    "E9",     # pycodestyle runtime errors
    "W",      # pycodestyle warnings
    "I",      # isort (import sorting) - ADR-0002
    "B",      # flake8-bugbear (common bugs)
    "UP",     # pyupgrade (modern Python)
    "TCH",    # flake8-type-checking - ADR-0002
]
```

Also added:

- `[tool.ruff.lint.isort]` — known-first-party modules
- `[tool.ruff.lint.flake8-type-checking]` — Protocol as runtime-evaluated base

### T3: High-Level Service Protocols

Created `core/protocols/service_protocols.py` (287 lines) with:

| Protocol            | Purpose                  | Methods                                                    |
| ------------------- | ------------------------ | ---------------------------------------------------------- |
| `MemoryService`     | Unified memory interface | `store()`, `retrieve()`, `search()`                        |
| `LLMService`        | Unified LLM interface    | `complete()`, `chat()`, `embed()`                          |
| `GovernanceService` | Policy enforcement       | `check_policy()`, `enforce_limits()`, `request_approval()` |

All protocols are `@runtime_checkable` for isinstance() checks.

### T4: Protocol Registration

Updated `core/protocols/__init__.py`:

- Import: `from core.protocols.service_protocols import ...`
- Export: Added to `__all__` list

---

## Validation Results

| Check                                   | Result               |
| --------------------------------------- | -------------------- |
| py_compile service_protocols.py         | ✅                   |
| py_compile **init**.py                  | ✅                   |
| ruff check service_protocols.py         | ✅ All checks passed |
| YAML validation .pre-commit-config.yaml | ✅                   |
| TOML validation pyproject.toml          | ✅                   |
| Protocol execution test                 | ✅                   |

---

## What Was Skipped from PR #49

| PR Component                             | Reason Skipped                               |
| ---------------------------------------- | -------------------------------------------- |
| `core/patterns/singleton.py`             | Local `@register_singleton` is more advanced |
| `core/di/bootstrap_integration.py`       | Conflicts with production `bootstrap.py`     |
| `tests/unit/test_singleton_pattern.py`   | Tests unused pattern                         |
| Most of `service_protocols.py` structure | Adapted to local patterns                    |

---

## Architecture Decision

**High-level protocols complement (not replace) fine-grained protocols:**

```
Agent Code
    │
    └── MemoryService (high-level)
            │
            ├── CacheClient (fine-grained)
            ├── GraphClient (fine-grained)
            ├── VectorStore (fine-grained)
            └── MemoryRepository (fine-grained)
```

Agents use simple interface; complexity is encapsulated in service implementations.

---

## Files Modified

1. `.pre-commit-config.yaml` — +17 lines (ADR hooks)
2. `pyproject.toml` — +19 lines (ruff expansion)
3. `core/protocols/service_protocols.py` — NEW (287 lines)
4. `core/protocols/__init__.py` — +9 lines (registration)

**Total:** ~332 lines added

---

## Next Steps

1. Implement `MemoryService` in `MemorySubstrateService`
2. Create `LLMService` implementation wrapping OpenAI/Anthropic
3. Create `GovernanceService` implementation wrapping approval workflows
4. Add unit tests for new protocols
