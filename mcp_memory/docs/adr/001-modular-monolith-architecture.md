# ADR 001: Modular Monolith Architecture for L9 Memory System

**Status:** ACCEPTED
**Date:** 2026-01-25
**Authors:** L9 Engineering (Igor Beylin)
**Affects:** Core kernel, all substrates, control plane

## Context

L9 memory system began as monolith with tightly coupled responsibilities:
- Packet validation mixed with routing logic (kernel)
- Safety checks intertwined with memory operations
- Configuration scattered across singletons
- Observability logic embedded in business code

This coupling causes difficult testing, risk of side effects, unclear ownership, and harder scaling.

Frontier AI labs solve this via modular monoliths: single deployment with strict internal boundaries, typed interfaces, and clear data flow.

## Decision

Refactor into five bounded contexts:

1. **Kernel** (mcp_memory/src/kernel/): Orchestration and packet protocol
2. **Safety** (mcp_memory/src/safety/): Policy enforcement and security events
3. **Memory Substrate** (mcp_memory/src/memory_substrate/): Semantic storage and retrieval
4. **Observability** (mcp_memory/src/observability/): Logging, tracing, metrics
5. **Control Plane** (mcp_memory/src/control_plane/): Configuration, secrets, feature flags

Data flow:
```
HTTP Request -> Kernel.Orchestrator
    -> Safety.SafetyService.check_query()
    -> Memory_Substrate.SubstrateService.execute()
    -> Observability (logging/tracing)
All config from Control_Plane.get_settings()
```

## Benefits

- Testability: Each module tested in isolation
- Ownership: Clear CODEOWNERS mapping
- Scalability: Module extraction to microservices trivial
- Clarity: Responsibility boundaries explicit
- Safety: Type checking prevents violations

## Verification

- [x] Module __init__.py files created
- [ ] Abstract base classes defined
- [ ] Tests verify module isolation
- [ ] All imports flow through interfaces
- [ ] CODEOWNERS file updated
