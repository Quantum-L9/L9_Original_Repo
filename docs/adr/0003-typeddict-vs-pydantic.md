# ADR-0003: TypedDict vs Pydantic for LangGraph State

## Status

**Status:** Accepted  
**Date:** 2026-01-11  
**Author:** @l-cto  
**Stakeholders:** @langgraph-team, @agents-team  
**Supersedes:** None  
**Superseded by:** None

## Context

L9 uses both LangGraph for workflow orchestration and Pydantic for data validation. A decision was needed on which type system to use for LangGraph state schemas.

**LangGraph Requirements:**
- `StateGraph` requires dict-based state for state merging
- State must be mutable and support partial updates
- State schema must be compatible with LangGraph's reducer functions

**Pydantic Strengths:**
- Runtime validation of data
- Automatic serialization/deserialization
- Rich type system with constraints
- IDE support and type checking

**TypedDict Strengths:**
- Native Python type hints (no runtime overhead)
- Dict-compatible (works with LangGraph)
- Lightweight and fast
- Supports structural typing

The question was: Should we use TypedDict or Pydantic for LangGraph state schemas?

## Decision

**Use TypedDict for LangGraph state, Pydantic BaseModel for everything else.**

Specifically:
- **TypedDict:** LangGraph state schemas (`SubstrateGraphState`, `ResearchGraphState`, etc.)
- **Pydantic:** API models, database models, external data validation

**Conversion Pattern:**
```python
# Entry: Pydantic → TypedDict
state: SubstrateGraphState = {
    "envelope": envelope.model_dump(mode="json"),
    "errors": []
}

# Exit: TypedDict → Pydantic (if needed)
result = PacketEnvelope.model_validate(state["envelope"])
```

## Rationale

1. **LangGraph Compatibility** - TypedDict is dict-based, works seamlessly with `StateGraph`
2. **No Runtime Overhead** - TypedDict is just type hints, no validation cost
3. **Pydantic Where It Matters** - Use Pydantic for external data (API, DB) where validation is critical
4. **Best of Both Worlds** - TypedDict for performance, Pydantic for safety
5. **Clear Boundaries** - TypedDict inside LangGraph, Pydantic at boundaries

## Alternatives Considered

### Alternative 1: Use Pydantic for Everything

- **Pros:** Consistent type system, runtime validation everywhere
- **Cons:** LangGraph requires dict-based state, Pydantic models are not dicts
- **Why rejected:** Incompatible with LangGraph's state merging

### Alternative 2: Use TypedDict for Everything

- **Pros:** Consistent type system, no runtime overhead
- **Cons:** No runtime validation for external data (API, DB)
- **Why rejected:** Validation is critical for external data

### Alternative 3: Use Plain Dicts (No Type Hints)

- **Pros:** Maximum flexibility, no type system constraints
- **Cons:** No type safety, no IDE support, error-prone
- **Why rejected:** Type safety is essential for large codebases

### Alternative 4: Use Dataclasses for LangGraph State

- **Pros:** Native Python, lightweight, type hints
- **Cons:** Not dict-based, incompatible with LangGraph state merging
- **Why rejected:** Same issue as Pydantic models

## Consequences

### Positive

1. **LangGraph Compatibility** - TypedDict works seamlessly with `StateGraph`
2. **Performance** - No runtime overhead for LangGraph state
3. **Type Safety** - Full type hints and IDE support
4. **Validation Where Needed** - Pydantic validates external data
5. **Clear Boundaries** - TypedDict inside, Pydantic at edges

### Negative

1. **Two Type Systems** - Engineers need to know when to use each
2. **Conversion Overhead** - Need to convert between TypedDict and Pydantic
3. **No Runtime Validation** - TypedDict doesn't validate at runtime
4. **Potential Confusion** - May be unclear which to use in edge cases

### Neutral

1. **Learning Curve** - Engineers need to understand both type systems
2. **Documentation Needed** - Clear guidelines on when to use each

## Implementation

### Migration Path

1. **Define TypedDict Schemas**
   ```python
   from typing import TypedDict, NotRequired
   
   class SubstrateGraphState(TypedDict):
       envelope: dict  # Pydantic model dumped to dict
       errors: list[str]
       context: NotRequired[dict]
   ```

2. **Convert Pydantic to TypedDict at Entry**
   ```python
   # Entry point to LangGraph
   state: SubstrateGraphState = {
       "envelope": envelope.model_dump(mode="json"),
       "errors": []
   }
   ```

3. **Convert TypedDict to Pydantic at Exit**
   ```python
   # Exit point from LangGraph
   result = PacketEnvelope.model_validate(state["envelope"])
   ```

4. **Update Documentation**
   - Create `l9/langgraph/TYPEDDICT_VS_PYDANTIC.md`
   - Update `l9/langgraph/README.md` with guidelines
   - Add examples to agent documentation

### Rollback Strategy

If this approach proves problematic:
1. Convert TypedDict schemas to Pydantic
2. Use `model_dump()` to convert Pydantic to dict for LangGraph
3. Accept the runtime overhead of Pydantic validation

### Validation

Success criteria:
- ✅ All LangGraph state schemas use TypedDict
- ✅ All API/DB models use Pydantic
- ✅ Conversion pattern documented
- ✅ No type errors in IDE
- ✅ All tests passing

## Metadata

**Category:** Architecture  
**Impact:** Medium  
**Tier:** T2 (Reversible, requires tests)  
**Related PRs:** None (completed before ADR system)  
**Related ADRs:** None  
**References:**
- `l9/langgraph/README.md`
- `l9/langgraph/TYPEDDICT_VS_PYDANTIC.md`
- [LangGraph State Documentation](https://langchain-ai.github.io/langgraph/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Notes

This decision was made and implemented on 2026-01-11, before the ADR system was established. This ADR is a retroactive documentation of that decision.

The key insight is that TypedDict and Pydantic serve different purposes:
- **TypedDict:** Type hints for internal data structures (LangGraph state)
- **Pydantic:** Runtime validation for external data (API, DB)

This pattern should be followed for all future LangGraph integrations.
