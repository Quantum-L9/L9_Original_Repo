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

### Quick Start Example

**Before (in `singleton_registry.py`):**
```python
# Manual registration with try/except block
try:
    from runtime.redis_client import get_redis_client, close_redis_client
    registry.register(
        name="redis_client",
        module_path="runtime.redis_client",
        getter=get_redis_client,
        closer=close_redis_client,
        # ... more config ...
    )
except ImportError:
    pass
```

**After (in `runtime/redis_client.py`):**
```python
from core.singleton_auto_registry import register_singleton, register_singleton_closer

@register_singleton(category="core", lifecycle=SingletonLifecycle.STARTUP)
async def get_redis_client():
    # ... implementation ...
    return redis_client

@register_singleton_closer("redis_client")
async def close_redis_client():
    # ... cleanup ...
    pass
```

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

### Quick Start Example

**Before (in `core/coordination/event_queue.py`):**
```python
class EventKind(Enum):
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    # ... more hardcoded events ...
```

**After (in any module):**
```python
from core.event_type_registry import register_event_type

register_event_type(
    name="my_custom_event",
    category="custom",
    description="A custom event for my feature."
)

# Check if registered
assert is_event_type_registered("my_custom_event")

# Create dynamic enum for backward compatibility
CustomEvents = create_dynamic_event_enum("custom")
assert CustomEvents.MY_CUSTOM_EVENT.value == "my_custom_event"
```

### Impact

- **Eliminates hardcoded enums**, making the event system extensible.
- **Allows plugins and extensions** to define their own event types.
- **Reduces merge conflicts** in core event files.

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
