# ADR 0014: DORA Metadata Block Pattern

## Status

Accepted

## Pattern

Every Python module includes `__dora_meta__` dict at module top for machine-readable component metadata.

## Files

- 565+ files contain `__dora_meta__`
- `runtime/dora.py` - DORA runtime utilities
- `scripts/audit/inject_dora_complete.py` - Auto-injection script

## Import Block

```python
# No imports needed — __dora_meta__ is a plain dict
```

## Minimal Implementation

```python
"""
Module docstring here.
"""

__dora_meta__ = {
    "component_name": "Human Readable Name",
    "module_version": "1.0.0",
    "created_by": "Author Name",
    "created_at": "2026-01-20T00:00:00Z",
    "updated_at": "2026-01-20T00:00:00Z",
    "layer": "core",           # foundation|core|integration|api|service
    "domain": "memory",        # memory|governance|agents|tools|etc.
    "module_name": "package.module",
    "type": "service",         # service|adapter|schema|dataclass|utility
    "status": "active",        # active|deprecated|experimental
    "integrates_with": {
        "api_endpoints": ["/api/v1/endpoint"],
        "datasources": ["postgres", "redis"],
        "memory_layers": ["packet_store", "semantic_memory"],
        "imported_by": ["other.module"],
    },
}

# Rest of module code...
```

## Schema Reference

```python
__dora_meta__: dict = {
    # Required fields
    "component_name": str,      # Human-readable name
    "module_version": str,      # SemVer: "1.0.0"
    "created_by": str,          # Author name
    "created_at": str,          # ISO 8601 timestamp
    "updated_at": str,          # ISO 8601 timestamp
    "layer": str,               # foundation|core|integration|api|service
    "domain": str,              # Domain classification
    "module_name": str,         # Python module path
    "type": str,                # Component type
    "status": str,              # active|deprecated|experimental

    # Optional but recommended
    "integrates_with": {
        "api_endpoints": list[str],
        "datasources": list[str],
        "memory_layers": list[str],
        "imported_by": list[str],
    },
    "architecture_patterns": list[str],  # ["Pattern name (ADR-XXXX)"]
    "pep_compliance": list[str],         # ["PEP 563", "PEP 544"]
}
```

## Anti-Pattern Example

```python
# ❌ WRONG — Missing __dora_meta__ entirely
"""Module docstring."""

def my_function():
    pass

# ❌ WRONG — Incomplete __dora_meta__
__dora_meta__ = {
    "name": "Foo",  # Wrong key names
}

# ✅ CORRECT — Full __dora_meta__ after docstring
"""Module docstring."""

__dora_meta__ = {
    "component_name": "Foo Service",
    "module_version": "1.0.0",
    # ... all required fields
}
```

## Rules

1. EVERY Python module MUST have `__dora_meta__`
2. Place immediately after module docstring
3. Update `updated_at` when modifying file
4. Run `scripts/audit/inject_dora_complete.py` for new files
5. DO NOT place before docstring

## AI Guidance

**DO:**

- Preserve `__dora_meta__` when editing files
- Update `updated_at` timestamp on changes
- Add new imports to `imported_by` list
- Copy from existing file and modify

**DO NOT:**

- Remove `__dora_meta__` as "unused code"
- Delete `__dora_footer__` as "dead code"
- Flag DORA blocks as "unnecessary metadata"
- Move DORA blocks from their position after docstring
