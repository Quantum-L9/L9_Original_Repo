# Package Wiring Audit: core

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `core`

Files checked: 10
- WIRED: 0
- PARTIAL: 9
- ORPHAN: 1
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `core/auto_registry.py` | 6 | 1 | Y | - | PARTIAL |
| `core/config_constants.py` | 8 | 0 | - | - | PARTIAL |
| `core/decorators.py` | 295 | 134 | - | - | PARTIAL |
| `core/error_tracking.py` | 3 | 0 | - | - | PARTIAL |
| `core/event_type_registry.py` | 2 | 1 | Y | - | PARTIAL |
| `core/fastapi_lifespan.py` | 0 | 0 | - | - | ORPHAN |
| `core/governance_integration.py` | 1 | 0 | - | - | PARTIAL |
| `core/moduleregistry.py` | 3 | 1 | Y | - | PARTIAL |
| `core/singleton_auto_registry.py` | 18 | 3 | Y | - | PARTIAL |
| `core/singleton_registry.py` | 1 | 2 | - | - | PARTIAL |

## Level C: API Instantiation — `core`

API Status: **SHOULD_HAVE_API**
Symbols checked: 46
- USED: 22
- TEST_ONLY: 7
- UNUSED: 17

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `RegistryError` | 0 | 0 | UNUSED |
| `ComponentNotFoundError` | 0 | 0 | UNUSED |
| `must_stay_async_route` | 0 | 0 | UNUSED |
| `must_stay_async_protocol` | 0 | 0 | UNUSED |
| `must_stay_async_interface` | 0 | 0 | UNUSED |
| `get_error_chain` | 0 | 0 | UNUSED |
| `get_errors_by_type` | 0 | 0 | UNUSED |
| `get_error_stats` | 0 | 0 | UNUSED |
| `EventTypeConfig` | 0 | 0 | UNUSED |
| `register_event_category` | 0 | 1 | TEST_ONLY |
| `discover_event_types` | 0 | 0 | UNUSED |
| `get_event_types_by_category` | 0 | 0 | UNUSED |
| `get_event_categories` | 0 | 1 | TEST_ONLY |
| `is_event_type_registered` | 0 | 1 | TEST_ONLY |
| `create_dynamic_event_enum` | 0 | 1 | TEST_ONLY |
| `validate_event_payload` | 0 | 0 | UNUSED |
| `get_event_type_snapshot` | 0 | 0 | UNUSED |
| `SingletonServiceConfig` | 0 | 0 | UNUSED |
| `get_all_singleton_services` | 0 | 1 | TEST_ONLY |
| `get_singleton_services_by_category` | 0 | 1 | TEST_ONLY |
| `get_singleton_services_by_lifecycle` | 0 | 0 | UNUSED |
| `get_singleton_service_snapshot` | 0 | 0 | UNUSED |
| `SingletonEntry` | 0 | 0 | UNUSED |
| `SingletonRegistry` | 0 | 1 | TEST_ONLY |

**Recommended `__all__` entries (used externally):**
- `AutoRegistry`
- `DuplicateRegistrationError`
- `GovernanceIntegration`
- `ModuleDefinition`
- `ModuleRegistry`
- `ModuleStatus`
- `SingletonLifecycle`
- `ValidationError`
- `discover_singleton_services`
- `get_all_event_types`
- `get_allowed_scopes_for_caller`
- `get_default_project_id`
- `get_default_scope_for_caller`
- `get_singleton_registry`
- `log_error_to_graph`
- `must_stay_async`
- `register_core_event_types`
- `register_event_type`
- `register_singleton`
- `register_singleton_closer`
- `register_singleton_service`
- `wire_singletons_to_registry`
