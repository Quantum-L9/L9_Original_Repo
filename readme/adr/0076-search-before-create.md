# ADR-0076: Search Before Create

**Status:** Accepted  
**Date:** 2026-01-31  
**Author:** Igor Beylin  

## Context

Creating new files when similar functionality already exists leads to duplicate implementations, integration headaches, and maintenance burden.

Example incident: PR #30 created `memory/deduplication.py` with new `DeduplicationEngine`, but `memory/consolidation.py` already had `_run_deduplication()` method. Result: Two implementations doing the same thing, requiring post-merge integration.

## Decision

**Policy: Always search for existing solutions before creating new files.**

### Search Protocol

Before creating ANY new file:

1. **SEARCH** — Check if similar functionality exists
   - `grep -r "function_name\|ClassName" .`
   - Check related modules
   - Search for similar patterns

2. **ASK** — If similar code found:
   - "I found existing `[file]` with `[function]`. Should I enhance that or create new?"

3. **INTEGRATE** — Prefer enhancing existing code:
   - Add to existing module
   - Extend existing class
   - Import and compose

### When to Create New vs Enhance Existing

| Scenario | Action |
|----------|--------|
| Exact functionality exists | Use existing |
| Similar functionality exists | Enhance existing |
| Related module exists | Add to module |
| Completely new domain | Create new file |
| User explicitly requests new file | Create new file |

### Integration Patterns

```python
# ❌ BAD — Creating parallel implementation
# memory/new_deduplication.py
class NewDeduplicationEngine:
    async def deduplicate(self): ...

# ✅ GOOD — Enhancing existing
# memory/consolidation.py
from memory.deduplication import DeduplicationEngine

async def _run_deduplication(self):
    engine = DeduplicationEngine(...)  # Use new engine
    return await engine.deduplicate_packets(...)
```

### Search Commands

```bash
# Find similar functions
grep -rn "def similar_name" --include="*.py"

# Find similar classes
grep -rn "class SimilarName" --include="*.py"

# Find imports of related module
grep -rn "from related_module import" --include="*.py"

# Check if pattern exists
rg "pattern_name" -t py
```

### Anti-Patterns

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| "I'll create a new file for this" | Didn't search first |
| "This is cleaner as separate" | Justifying duplication |
| "I didn't know that existed" | Didn't search |
| Creating `utils2.py` | Clear duplication signal |

## Implementation

### Pre-Create Checklist

Before creating any new file:

- [ ] Searched for similar functionality
- [ ] Checked related modules
- [ ] Asked user if integration preferred
- [ ] Documented why new file is needed (if creating)

### Code Review Signal

If PR creates new file with similar name to existing:
- Flag for review
- Ask: "Why not enhance existing `[file]`?"

## Consequences

### Positive
- No duplicate implementations
- Easier maintenance
- Smaller codebase
- Clear ownership

### Negative
- Initial search takes time
- Existing code may need refactoring to accept enhancement

## Related
- ADR-0075: Ask Before Build
