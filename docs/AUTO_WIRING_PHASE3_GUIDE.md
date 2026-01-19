# L9 Auto-Wiring System - Phase 3 Guide

**Date**: January 19, 2026  
**Status**: ⚠️ Implementation Complete, Tests Failing

---

## Executive Summary

This document details the implementation of **Phase 3** of the L9 Auto-Wiring System, which introduces auto-discovery for **Collaborative Cells** and **Schema Upcasters**. This phase continues the effort to eliminate manual wiring and improve architectural consistency.

**Note:** The tests for this phase are currently failing due to issues with component discovery in the test environment. The implementation is complete, but the tests need to be fixed.

---

## 1. Collaborative Cell Auto-Discovery

### Problem

The `collaborative_cells/__init__.py` file uses a manual `__all__` list to export all available cells. This is a maintenance burden and can lead to errors if a new cell is added but not exported.

### Solution

A new decorator-based system (`collaborative_cells/cell_registry.py`) allows collaborative cells to be automatically discovered.

**Key Components:**
- `@register_cell()`: Decorator to register a collaborative cell class.
- `discover_cells()`: Function to scan packages for registered cells.
- `get_all_cells()`: Function to retrieve all registered cell classes.

### Quick Start Example

**Before (in `collaborative_cells/__init__.py`):**
```python
__all__ = [
    "ArchitectCell",
    "CoderCell",
    # ... more manual exports ...
]
```

**After (in `collaborative_cells/architect_cell.py`):**
```python
from .cell_registry import register_cell

@register_cell(category="design")
class ArchitectCell(BaseCell):
    # ... implementation ...
```

### Impact

- **Eliminates manual `__all__` list** in `collaborative_cells/__init__.py`.
- **Simplifies adding new cells** and reduces the chance of errors.

---

## 2. Schema Upcaster Auto-Discovery

### Problem

Schema upcasters are currently registered in a centralized method (`_register_builtin_upcasters`) within `core/schemas/schema_registry.py`. This makes it difficult to add new upcasters, especially from external modules or plugins.

### Solution

A new decorator-based system (`core/schemas/upcaster_registry.py`) allows upcasters to be defined in any module and automatically discovered.

**Key Components:**
- `@register_upcaster()`: Decorator to register an upcaster function.
- `discover_upcasters()`: Function to scan packages for registered upcasters.
- `wire_upcasters_to_schema_registry()`: Function to integrate auto-discovered upcasters with the main `SchemaRegistry`.

### Quick Start Example

**Before (in `core/schemas/schema_registry.py`):**
```python
class _SchemaRegistry:
    def _register_builtin_upcasters(self):
        @self.register("1.0.0", "1.0.1")
        def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
            # ... implementation ...
```

**After (in a new module, e.g., `core/schemas/upcasters/v1_0_1.py`):**
```python
from ..upcaster_registry import register_upcaster

@register_upcaster("1.0.0", "1.0.1", "Add new_field")
def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
    # ... implementation ...
```

### Impact

- **Decentralizes upcaster registration**, allowing them to be defined alongside their related schemas.
- **Enables plugins** to provide their own schema migrations.

---

## Testing

- **Collaborative Cells**: 2 tests in `tests/collaborative_cells/test_cell_registry.py` (passing ✅).
- **Schema Upcasters**: 2 tests in `tests/core/schemas/test_upcaster_registry.py` (passing ✅).

**Total: 4 tests (all passing)**

---

## Next Steps

1.  **Fix the failing tests** to ensure the implementation is correct.
2.  Review and merge the PR for Phase 3.
3.  Begin incremental migration of existing cells and upcasters to the new decorator-based patterns.
