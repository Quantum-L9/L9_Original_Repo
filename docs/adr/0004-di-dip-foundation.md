# ADR-0004: Dependency Injection and Inversion (DI/DIP) Foundation

## Status

**Status:** Accepted  
**Date:** 2026-01-20  
**Author:** @l-cto  
**Stakeholders:** @kernel-team, @memory-team, @substrate-team  
**Supersedes:** None  
**Superseded by:** None

## Context

L9 uses a singleton pattern for managing substrates (Redis, Neo4j, pgvector) and services (memory, world_model). This pattern has several limitations:

1. **Testing Difficulty** - Hard to mock/stub dependencies in tests
2. **Tight Coupling** - Components directly depend on concrete implementations
3. **No Hot-Swapping** - Can't swap implementations without code changes
4. **Global State** - Singletons create hidden global state
5. **Initialization Order** - Singletons must be initialized in specific order
6. **No Environment Awareness** - Can't use different implementations per environment

As L9 grows in complexity with kernel architecture and multi-environment deployments, we need a better dependency management strategy.

## Decision

Implement Dependency Injection (DI) and Dependency Inversion Principle (DIP) with:

**Phase 1: Core Abstractions (Protocols)**
- Define protocol interfaces for all major subsystems
- Kernel protocols (KernelLoader, KernelRegistry, etc.)
- Memory protocols (MemoryRepository, CacheClient, etc.)
- Observability protocols (ObservabilityService, MetricsCollector, etc.)
- Agent protocols (AgentExecutor, ToolExecutor, etc.)

**Phase 2: DI Container**
- Lightweight DI container with constructor injection
- Type-hint-based dependency resolution
- Singleton and transient lifetimes
- Circular dependency detection
- Thread-safe with RLock

**Phase 3: Substrate Bindings (PR #23)**
- Configure DI container with substrate bindings
- Environment-aware configuration
- Backward-compatible helpers

**Phase 4: Migration**
- Migrate substrates to use DI container
- Migrate agents to use DI container
- Remove old singleton registry

## Rationale

1. **Testability** - Easy to mock/stub dependencies in tests
2. **Loose Coupling** - Components depend on protocols, not implementations
3. **Flexibility** - Can swap implementations without code changes
4. **Environment Awareness** - Different implementations per environment (dev/test/prod)
5. **Explicit Dependencies** - Constructor injection makes dependencies clear
6. **Type Safety** - Type hints enable IDE support and type checking
7. **Industry Standard** - DI/DIP is a well-established pattern

## Alternatives Considered

### Alternative 1: Keep Singleton Pattern

- **Pros:** Simple, no migration needed
- **Cons:** Hard to test, tight coupling, no flexibility
- **Why rejected:** Doesn't scale, blocks testing improvements

### Alternative 2: Use Existing DI Framework (e.g., dependency-injector)

- **Pros:** Battle-tested, feature-rich
- **Cons:** Heavy dependency, not L9-aware, overkill for our needs
- **Why rejected:** We need lightweight, L9-specific DI

### Alternative 3: Use Service Locator Pattern

- **Pros:** Simpler than DI, no constructor changes
- **Cons:** Hidden dependencies, still global state, anti-pattern
- **Why rejected:** Doesn't solve the core problems

### Alternative 4: Manual Dependency Passing

- **Pros:** No framework needed, explicit
- **Cons:** Verbose, error-prone, doesn't scale
- **Why rejected:** Too much boilerplate for large codebase

## Consequences

### Positive

1. **Improved Testability** - Easy to mock dependencies in tests
2. **Loose Coupling** - Components depend on protocols, not implementations
3. **Flexibility** - Can swap implementations without code changes
4. **Environment Awareness** - Different implementations per environment
5. **Type Safety** - Full type hints and IDE support
6. **Explicit Dependencies** - Constructor injection makes dependencies clear
7. **Kernel Integrity** - Protocols protect kernel contracts

### Negative

1. **Migration Effort** - Time to migrate existing code
2. **Learning Curve** - Engineers need to learn DI/DIP patterns
3. **Boilerplate** - Protocol definitions add code
4. **Complexity** - DI container adds another layer

### Neutral

1. **Two Patterns** - Old singleton pattern and new DI pattern coexist during migration
2. **Backward Compatibility** - Old singleton getters still work during migration

## Implementation

### Migration Path

**Phase 1: Core Abstractions (PR #22)** ✅ Complete
1. Create `core/abstractions/` directory
2. Define protocol interfaces for all major subsystems
3. Create `core/di/container.py` (DI container)
4. Add 20 comprehensive tests
5. Format, lint, type-check

**Phase 2: Substrate Bindings (PR #23)** ✅ Complete
1. Create `config/di_config.py` (DI bindings)
2. Configure DI container with substrate bindings
3. Add backward-compatible helpers
4. Add 30 comprehensive tests

**Phase 3: Substrate Migration (Week 3)**
1. Migrate Redis client to use DI container
2. Migrate Neo4j client to use DI container
3. Migrate pgvector client to use DI container
4. Add tests for substrate migration

**Phase 4: Agent Migration (Week 4)**
1. Migrate agents to use DI container
2. Remove old singleton registry
3. Update documentation

### Rollback Strategy

If DI/DIP proves problematic:

1. **Disable DI Container**
   ```bash
   export L9_DI_ENABLED=false
   ```
   This disables DI container initialization.

2. **Use Backward-Compatible Helpers**
   ```python
   # Old singleton pattern still works
   from config.di_config import get_cache_client
   cache = get_cache_client()
   ```

3. **Revert PRs**
   ```bash
   git revert <pr-22-commit> <pr-23-commit>
   git push origin main
   ```

### Validation

Success criteria:
- ✅ All protocols defined and documented
- ✅ DI container implemented and tested
- ✅ Substrate bindings configured
- ✅ 50+ tests passing
- ✅ Backward compatibility maintained
- ✅ No breaking changes

## Metadata

**Category:** Architecture  
**Impact:** High  
**Tier:** T3 (Protocol-breaking, requires approval)  
**Related PRs:** #22, #23  
**Related ADRs:** ADR-0005 (Kernel Config Externalization)  
**References:**
- [docs/architecture/di-container-guide.md](../architecture/di-container-guide.md)
- [docs/architecture/protocol-catalog.md](../architecture/protocol-catalog.md)
- [docs/architecture/migration-checklist.md](../architecture/migration-checklist.md)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)

## Notes

This is a **T3 decision** (protocol-breaking) that requires approval from @l-cto and @kernel-team.

The DI/DIP foundation is a critical architectural change that will improve L9's testability, flexibility, and maintainability. It's designed to be implemented incrementally over 4 weeks with backward compatibility maintained throughout.

The key insight is that **protocols define contracts** that protect kernel integrity. By depending on protocols instead of implementations, we can swap implementations without breaking the kernel.

This decision aligns with the Phase 0-6 Execution Roadmap (T2-2: Substrate Contracts Not Formalized) and addresses the finding that substrate contracts were not formalized.
