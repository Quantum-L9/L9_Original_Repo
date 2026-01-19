# L9 Auto-Wiring System - Phase 2 Guide

**Date**: January 18, 2026  
**Status**: ✅ Complete and Ready for Review  

---

## Executive Summary

This document details the implementation of **Phase 2** of the L9 Auto-Wiring System, which introduces auto-registration for **Singleton Services** and **Event Types**. This phase builds on the core `AutoRegistry` framework to further eliminate manual wiring and enhance architectural consistency.

---

## 1. Singleton Service Auto-Registration

### Problem

The existing `singleton_registry.py` contains a monolithic function with **26+ manual `try/except` blocks** for registering each singleton service. This is a major source of boilerplate and makes adding new services tedious and error-prone.

### Solution

A new decorator-based system (`core/singleton_auto_registry.py`) allows singleton services to self-register from their own modules.

**Key Components:**
- `@register_singleton()`: Decorator to register a singleton getter function.
- `@register_singleton_closer()`: Decorator to associate a closer function.
- `discover_singleton_services()`: Function to scan packages for registered singletons.
- `wire_singletons_to_registry()`: Function to wire auto-registered services to the main `SingletonRegistry`.

### Impact

- **Eliminates ~300 lines** of boilerplate in `singleton_registry.py`.
- **Decentralizes registration**, making it easier to add/remove services.
- **Improves maintainability** and reduces merge conflicts.

---

## 2. Event Type Auto-Registration

### Problem

Event types in L9 are defined as hardcoded `Enum` classes (`EventKind`, `SecurityEventType`). Adding a new event type requires modifying these core enum files, which is inflexible and can lead to merge conflicts.

### Solution

A new dynamic event type registry (`core/event_type_registry.py`) allows event types to be registered at runtime without modifying enums.

**Key Components:**
- `register_event_type()`: Function to register a new event type.
- `register_event_category()`: Helper to register multiple events in a category.
- `create_dynamic_event_enum()`: Function to create a dynamic `Enum` for backward compatibility.
- `is_event_type_registered()`: Function to check if an event type exists.

### Impact

- **Eliminates hardcoded enums**, making the event system extensible.
- **Allows plugins and extensions** to define their own event types.
- **Reduces merge conflicts** in core event files.

---

## 3. Migration Guide

### Step 1: Pilot with 1-2 Singletons

Start with a low-risk singleton like `research_settings`. Add `@register_singleton` decorator to the getter function.

### Step 2: Wire Discovery into Server Lifespan

Add to `api/server.py` lifespan:
- `discover_singleton_services("runtime")`
- `discover_singleton_services("memory")`
- `wire_singletons_to_registry(get_singleton_registry())`

### Step 3: Incremental Migration

Migrate singletons **one category at a time**:

1. **Config singletons** (lowest risk): `research_settings`
2. **Client singletons**: `memory_client`, `world_model_client`
3. **Memory singletons**: `query_classifier`, `housekeeping_engine`
4. **Core singletons** (highest risk, do last): `redis_client`, `neo4j_client`

For each singleton:
1. Add `@register_singleton` decorator to the getter function
2. Add `@register_singleton_closer` decorator to the closer function (if exists)
3. Remove the corresponding `try/except` block from `_register_core_singletons()`
4. Run tests to verify

### Step 4: Cleanup

Once all singletons are migrated, simplify `_register_core_singletons()` to just discovery calls.

### Migration Checklist

- [ ] Add `@register_singleton` to getter function
- [ ] Add `@register_singleton_closer` to closer function (if exists)
- [ ] Specify correct `category` and `lifecycle`
- [ ] Add `dependencies` list if singleton depends on others
- [ ] Remove manual registration from `_register_core_singletons()`
- [ ] Run `pytest tests/core/test_singleton_auto_registry.py`
- [ ] Run full test suite to verify no regressions

---

## Testing

- **Singleton Services**: 4 comprehensive tests in `tests/core/test_singleton_auto_registry.py`.
- **Event Types**: 5 comprehensive tests in `tests/core/test_event_type_registry.py`.

**Total: 9 tests (all passing ✅)**

---

## Next Steps

1. Review and merge the PR for Phase 2.
2. Begin incremental migration of existing singleton services to the new decorator-based pattern.
3. Refactor code that uses hardcoded event enums to use the new dynamic registry.
