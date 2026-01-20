# Core Module

**Path:** `core/`  
**Purpose:** Foundational logic and infrastructure for the L9 platform  
**Files:** 164 Python files  
**Last Updated:** 2026-01-18

---

## Overview

The `core` module contains the foundational components of the L9 Agentic Intelligence Platform. This is the heart of the system, providing essential services, governance, and infrastructure that all other modules depend on.

⚠️ **CRITICAL:** Changes to `core/` have system-wide impact. All modifications require careful review and testing.

## Architecture

### Major Subsystems

| Subsystem | Purpose | Key Files |
|---|---|---|
| **`agents/`** | Agent infrastructure | `executor.py`, `agent_instance.py`, `prompt_builder.py` |
| **`governance/`** | Policy enforcement and compliance | `policy_registry.py`, `credentials_policy.py` |
| **`schemas/`** | Data schemas and validation | `upcaster_registry.py`, `research_factory_nodes.py` |
| **`evaluation/`** | Agent and system evaluation | `evaluator.py` |
| **`bootstrap/`** | System initialization | `executor.py` |

### Core Registries

L9 uses a registry pattern for extensibility:

- **`singleton_registry.py`** - Central singleton management (380+ lines)
- **`auto_registry.py`** - Automatic component registration
- **`event_type_registry.py`** - Event type management
- **`policy_registry.py`** - Governance policy registry

## Key Concepts

### Singleton Registry

The `SingletonRegistry` is the backbone of L9's dependency injection:

```python
from core.singleton_registry import SingletonRegistry

# Get a singleton instance
memory_engine = await SingletonRegistry.get_memory_engine()
world_model = await SingletonRegistry.get_world_model_engine()

# Close singletons (cleanup)
await SingletonRegistry.close_memory_engine()
```

**Critical Methods:**
- `get_memory_engine()` - Memory substrate access
- `get_world_model_engine()` - World model access
- `get_ws_orchestrator()` - WebSocket orchestration
- `get_cursor_memory_kernel()` - Cursor integration

### Governance System

All operations in L9 are governed by policies:

```python
from core.governance.policy_registry import PolicyRegistry

# Register a policy
PolicyRegistry.register("memory_scope", MemoryScopePolicy)

# Enforce a policy
await policy.enforce(context, action)
```

**Policy Types:**
- **Credentials Policy** - Secret management and detection
- **Memory Scope Policy** - Data access boundaries
- **Resource Limits** - Compute and API usage
- **Audit Policies** - Compliance and logging

### Agent Infrastructure

The `core/agents/` subsystem provides:

- **`executor.py`** - Agent execution engine (1,979 lines!)
- **`agent_instance.py`** - Agent lifecycle management (563 lines)
- **`prompt_builder.py`** - Kernel-aware prompt construction

### Schema Management

L9 uses a sophisticated schema system with upcasting:

```python
from core.schemas.upcaster_registry import UpcasterRegistry

# Register an upcaster for schema migration
UpcasterRegistry.register("v1_to_v2", V1ToV2Upcaster)

# Upcast data
new_data = await UpcasterRegistry.upcast(old_data, "v2")
```

## Usage

### Accessing Core Services

```python
from core.singleton_registry import SingletonRegistry

# Memory operations
memory = await SingletonRegistry.get_memory_engine()
await memory.store(key, value)

# World model operations
world_model = await SingletonRegistry.get_world_model_engine()
facts = await world_model.query(query)
```

### Implementing a Policy

```python
from core.governance.policy_registry import PolicyRegistry, BasePolicy

class MyPolicy(BasePolicy):
    async def enforce(self, context, action):
        if not self.is_allowed(context, action):
            raise PolicyViolationError("Action not allowed")
        return True

# Register
PolicyRegistry.register("my_policy", MyPolicy)
```

### Creating an Upcaster

```python
from core.schemas.upcaster_registry import BaseUpcaster

class V1ToV2Upcaster(BaseUpcaster):
    def upcast(self, data):
        # Transform v1 schema to v2
        return {
            **data,
            "new_field": self.compute_new_field(data)
        }
```

## Development Guidelines

### Modifying Core

⚠️ **WARNING:** Core modifications affect the entire system.

**Required Steps:**
1. **RFC (Request for Comments)** - Propose changes in team discussion
2. **Impact Analysis** - Identify all affected modules
3. **Backward Compatibility** - Maintain compatibility or provide migration path
4. **Comprehensive Testing** - Test all affected subsystems
5. **Documentation** - Update all relevant docs

### Code Quality Standards

Core code must meet the highest standards:

- ✅ **Type Hints** - All functions must have type annotations
- ✅ **Docstrings** - Comprehensive documentation required
- ✅ **Tests** - Minimum 80% coverage for core modules
- ✅ **Error Handling** - Explicit exception handling
- ✅ **Logging** - Structured logging for all operations

### Performance Considerations

Core modules are performance-critical:

- Avoid blocking I/O in async functions
- Use caching for expensive operations
- Profile before optimizing
- Monitor memory usage
- Benchmark critical paths

## Testing

```bash
# Run all core tests
pytest tests/core/

# Run specific subsystem tests
pytest tests/core/governance/
pytest tests/core/schemas/

# Run with coverage
pytest tests/core/ --cov=core --cov-report=html

# Run integration tests
pytest tests/integration/ -k core
```

## Configuration

Core configuration is managed through:

- **`config/boot_overlay.yaml`** - Runtime overrides
- **Environment Variables** - System-level config
- **Kernel Policies** - Governance rules

## Subsystem Details

### core/agents/

Agent execution infrastructure:

- **`executor.py`** - Main agent execution engine
- **`agent_instance.py`** - Agent lifecycle and state management
- **`prompt_builder.py`** - Kernel-aware prompt construction
- **`tool_executor.py`** - Tool invocation with governance

### core/governance/

Policy enforcement system:

- **`policy_registry.py`** - Central policy registry
- **`credentials_policy.py`** - Secret detection and management
- **`audit_logger.py`** - Compliance logging

### core/schemas/

Data schema management:

- **`upcaster_registry.py`** - Schema migration system
- **`research_factory_nodes.py`** - Research workflow schemas
- **`validation.py`** - Schema validation utilities

### core/evaluation/

System evaluation framework:

- **`evaluator.py`** - Agent and system evaluation
- **`metrics.py`** - Performance metrics
- **`benchmarks.py`** - Benchmark suite

## Troubleshooting

### Common Issues

**Singleton not initializing:**
```python
# Check singleton registry state
from core.singleton_registry import SingletonRegistry
print(SingletonRegistry._instances)
```

**Policy violations:**
- Review policy configuration in `config/policies/`
- Check audit logs for violation details
- Verify context has required permissions

**Schema migration failures:**
- Ensure upcasters are registered
- Verify schema versions are correct
- Check upcaster logic for errors

## Related Modules

- **`runtime/`** - Runtime execution (depends on core)
- **`agents/`** - Agent implementations (uses core infrastructure)
- **`memory/`** - Memory substrate (managed by core singletons)
- **`orchestration/`** - Multi-agent orchestration (uses core executor)

## Performance Metrics

**Key Performance Indicators:**

- Singleton initialization: < 100ms
- Policy enforcement: < 10ms per check
- Schema validation: < 5ms per document
- Agent execution overhead: < 50ms

## Security Considerations

Core modules handle sensitive operations:

- ✅ All secrets managed through governance
- ✅ Audit logging for all policy decisions
- ✅ Fail-closed behavior on errors
- ✅ Input validation on all public APIs
- ✅ Rate limiting on expensive operations

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for general guidelines.

### Core-Specific Guidelines

- All PRs to `core/` require two approvals
- Breaking changes require RFC and migration guide
- Performance regressions must be justified
- New subsystems require architecture review
- Security-sensitive changes require security review

---

**Module Maintainer:** L-CTO Agent  
**Last Audit:** 2026-01-18  
**Status:** Production  
**Complexity:** Very High (164 files, 380+ line functions)
