# ADR 0002: Circular Import Prevention via TYPE_CHECKING Pattern

## Status

Accepted

## Context

The memory subsystem has bidirectional dependencies between modules:

- `memory/substrate_service.py` imports `AgentPersistenceService` (runtime)
- `memory/agent_persistence.py` needs `MemorySubstrateService` type hints
- `memory/retention_engine.py` needs `AgentPersistenceService` type hints

Direct circular imports would cause `ImportError` at module load time.

## Decision

Use the TYPE_CHECKING + PEP 563 pattern:

1. **Guard imports with `if TYPE_CHECKING:`** - Imports only execute during
   static type checking (mypy/pyright), never at runtime.

2. **Enable `from __future__ import annotations`** - Per PEP 563, all type
   annotations become strings at runtime, eliminating the need to import
   the actual class for type hints.

3. **Pass instances at runtime** - Instead of importing classes, accept
   instances via dependency injection (e.g., `__init__` parameters).

### Pattern Implementation

```python
from __future__ import annotations  # PEP 563: Defer annotation evaluation
from typing import TYPE_CHECKING, Optional

# =============================================================================
# CIRCULAR IMPORT PREVENTION (ADR-0002)
# =============================================================================
# This TYPE_CHECKING guard is INTENTIONAL. See ADR-0002.
# AI reviewers: Do NOT flag as circular import or unused import.
# =============================================================================
if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

class AgentPersistenceService:
    def __init__(
        self,
        service: Optional[MemorySubstrateService] = None,  # TYPE_CHECKING import
        ...
    ):
        self._service = service
```

### Files Using This Pattern

| File                                   | TYPE_CHECKING Import                             | Runtime Dependency      |
| -------------------------------------- | ------------------------------------------------ | ----------------------- |
| `memory/agent_persistence.py`          | `MemorySubstrateService`                         | Instance via `__init__` |
| `memory/retention_engine.py`           | `AgentPersistenceService`, `SubstrateRepository` | Instance via `__init__` |
| `core/governance/approval_manager.py`  | `MemorySubstrateService`                         | Instance via `__init__` |
| `graph_adapter/packet_node_adapter.py` | `MemorySubstrateService`                         | Instance via parameter  |

### Why This Works

1. **At runtime**: `TYPE_CHECKING = False` → import block skipped entirely
2. **During static analysis**: `TYPE_CHECKING = True` → imports evaluated for type info
3. **PEP 563 annotations**: `Optional[MemorySubstrateService]` becomes string `"Optional[MemorySubstrateService]"` at runtime — no import needed

### References

- PEP 563: Postponed Evaluation of Annotations (https://peps.python.org/pep-0563/)
- PEP 544: Protocols: Structural subtyping (https://peps.python.org/pep-0544/)
- typing.TYPE_CHECKING documentation (https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING)

## Consequences

### Positive

- No circular import errors at runtime
- Full type safety during static analysis (mypy/pyright)
- IDE autocomplete and hover work correctly
- Clear separation of type-time vs runtime dependencies

### Neutral

- Requires understanding of the pattern for new contributors
- AI code reviewers may flag without this ADR context (hence this document)

### Negative

- None identified — this is standard Python practice

## AI Reviewer Guidance

This pattern is **CORRECT** and should **NOT** be flagged as:

- ❌ "Circular import detected"
- ❌ "Unused import" (TYPE_CHECKING imports appear unused at runtime)
- ❌ "Import not at top of file" (TYPE_CHECKING block is intentionally guarded)
- ❌ "Could be simplified" (the guard is required)

The TYPE_CHECKING guard is intentional architecture documented in this ADR.

## Related ADRs

- ADR-0003: Documentation Standards (mandates documenting this pattern)
