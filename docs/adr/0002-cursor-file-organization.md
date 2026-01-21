# ADR-0002: Cursor File Organization

## Status

**Status:** Accepted  
**Date:** 2026-01-11  
**Author:** @l-cto  
**Stakeholders:** @cursor-team, @agents-team  
**Supersedes:** None  
**Superseded by:** None

## Context

Cursor-related files were scattered across multiple directories in the L9 repository:
- `core/governance/cursor_memory_kernel.py`
- `tools/cursor_client.py`
- `scripts/cursor_check_mistakes.py`
- `memory/extractor/cursor_action_extractor.py`
- `readme/CURSOR-L9-INTEGRATION.md`
- `prompts/cursor-extraction-*.md`

This scattered organization made it difficult to:
1. Find all Cursor-related code
2. Understand the Cursor integration scope
3. Maintain Cursor functionality
4. Onboard new engineers to Cursor integration

The repository already had a pattern of organizing agent-specific code in `agents/` directory (e.g., `agents/codegenagent/`), but Cursor files didn't follow this pattern.

## Decision

Consolidate all Cursor-related files into `agents/cursor/` directory with the following structure:

```
agents/cursor/
├── __init__.py
├── cursor_memory_kernel.py
├── cursor_client.py
├── scripts/
│   └── cursor_check_mistakes.py
├── extractors/
│   └── cursor_action_extractor.py
├── docs/
│   └── CURSOR-L9-INTEGRATION.md
└── prompts/
    ├── cursor-extraction-*.md
    └── ...
```

Update import paths to:
```python
from agents.cursor import CursorMemoryKernel, create_cursor_memory_kernel, CursorClient
from agents.cursor.cursor_memory_kernel import SessionState, Lesson, TodoItem
```

## Rationale

1. **Consistency** - Matches existing `agents/codegenagent/` pattern
2. **Discoverability** - All Cursor code in one place
3. **Separation of Concerns** - Clear boundary between core L9 and Cursor integration
4. **Maintainability** - Easier to update/remove Cursor integration
5. **Scalability** - Pattern can be applied to other agent integrations

## Alternatives Considered

### Alternative 1: Keep Files in Original Locations

- **Pros:** No migration needed, no import path changes
- **Cons:** Poor organization, hard to find Cursor code, doesn't scale
- **Why rejected:** Doesn't address the core problem of scattered files

### Alternative 2: Create `integrations/cursor/` Directory

- **Pros:** Clear that Cursor is an integration, not a core agent
- **Cons:** Creates new top-level directory, inconsistent with `agents/` pattern
- **Why rejected:** `agents/` directory already exists and is the right place

### Alternative 3: Keep Some Files in Core (e.g., cursor_memory_kernel.py)

- **Pros:** Acknowledges that some Cursor code is "core" functionality
- **Cons:** Defeats the purpose of consolidation, still scattered
- **Why rejected:** All Cursor code should be in one place for clarity

## Consequences

### Positive

1. **Improved Organization** - All Cursor code in one logical location
2. **Easier Discovery** - New engineers can find Cursor code quickly
3. **Better Maintainability** - Easier to update/remove Cursor integration
4. **Consistent Pattern** - Matches `agents/codegenagent/` structure
5. **Clearer Boundaries** - Separates core L9 from Cursor integration

### Negative

1. **Import Path Changes** - Requires updating imports across codebase
2. **Migration Effort** - Time to move files and update references
3. **Potential Breakage** - Risk of missing import updates

### Neutral

1. **No Functional Changes** - Code behavior remains the same
2. **Documentation Updates** - Need to update docs with new paths

## Implementation

### Migration Path

1. **Create Directory Structure**
   ```bash
   mkdir -p agents/cursor/{scripts,extractors,docs,prompts}
   ```

2. **Move Files**
   ```bash
   mv core/governance/cursor_memory_kernel.py agents/cursor/
   mv tools/cursor_client.py agents/cursor/
   mv scripts/cursor_check_mistakes.py agents/cursor/scripts/
   mv memory/extractor/cursor_action_extractor.py agents/cursor/extractors/
   mv readme/CURSOR-L9-INTEGRATION.md agents/cursor/docs/
   mv prompts/cursor-extraction-*.md agents/cursor/prompts/
   ```

3. **Update Imports**
   - Search for `from core.governance import cursor_memory_kernel`
   - Replace with `from agents.cursor import cursor_memory_kernel`
   - Search for `from tools import cursor_client`
   - Replace with `from agents.cursor import cursor_client`

4. **Update Documentation**
   - Update `agents/cursor/docs/CURSOR-L9-INTEGRATION.md` with new paths
   - Update any references in other docs

5. **Test**
   - Run full test suite
   - Verify no import errors
   - Verify Cursor functionality works

### Rollback Strategy

If issues arise:
1. Move files back to original locations
2. Revert import path changes
3. Revert documentation updates

### Validation

Success criteria:
- ✅ All Cursor files in `agents/cursor/`
- ✅ All imports updated and working
- ✅ All tests passing
- ✅ No import errors
- ✅ Documentation updated

## Metadata

**Category:** Architecture  
**Impact:** Medium  
**Tier:** T2 (Reversible, requires tests)  
**Related PRs:** None (completed before ADR system)  
**Related ADRs:** None  
**References:**
- `agents/cursor/docs/CURSOR-L9-INTEGRATION.md`
- `agents/codegenagent/` (pattern reference)

## Notes

This decision was made and implemented on 2026-01-11, before the ADR system was established. This ADR is a retroactive documentation of that decision.

The pattern established here (agent-specific code in `agents/<agent-name>/`) should be followed for future agent integrations.
