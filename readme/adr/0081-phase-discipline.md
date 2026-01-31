# ADR-0081: Phase Discipline

**Status:** Accepted  
**Date:** 2026-01-31  
**Author:** Igor Beylin  

## Context

Jumping directly to implementation without planning leads to scope creep, missed requirements, and incomplete solutions. The GMP (Governance Managed Process) phases exist to prevent this.

## Decision

**Policy: Follow the phases. No shortcuts. No jumping ahead.**

### GMP Phases

| Phase | Name | Purpose | Closure Condition |
|-------|------|---------|-------------------|
| 0 | PLAN | Define scope, files, actions | TODO plan locked |
| 1 | BASELINE | Capture current state | Tests pass, state documented |
| 2 | IMPLEMENT | Make changes | Code complete |
| 3 | ENFORCE | Apply constraints | Linting, formatting pass |
| 4 | VALIDATE | Run tests | All tests green |
| 5 | RECURSIVE VERIFY | Compare to Phase 0 | No scope drift |
| 6 | FINALIZE | Document, commit | Evidence summary complete |

### Phase 0 is Mandatory

Every significant change MUST start with Phase 0:

```markdown
## Phase 0: TODO Plan

**Files:**
- `path/to/file.py` — Lines 50-80 (Insert validation)
- `path/to/test.py` — Lines 100-120 (Add test case)

**Actions:**
- Insert input validation in `process_request()`
- Add unit test for edge case

**Expected Behavior:**
- Invalid input returns 400, not 500
- Test covers empty string case

**Out of Scope:**
- No changes to database layer
- No changes to API response format
```

### No Jumping to Phase 2

| Scenario | Wrong | Right |
|----------|-------|-------|
| "Quick fix" | Jump to implementation | Phase 0 → Phase 2 |
| "I know what to do" | Start coding | Lock plan first |
| "It's simple" | YOLO it | Even simple needs Phase 0 |

### Quick Actions Exception

QUICK_ACTIONS are allowed ONLY for:
- Single file
- No behavior change
- < 10 lines modified
- No protected files

When using quick action, state: `Scope: QUICK_ACTION; No behavior change, tests must still pass.`

### Phase Closure Evidence

Each phase requires evidence before advancing:

| Phase | Evidence Required |
|-------|-------------------|
| 0 | Written TODO plan with file paths |
| 1 | Baseline tests passing (output shown) |
| 2 | Code diff matches Phase 0 plan |
| 3 | Linting output clean |
| 4 | Test output showing all pass |
| 5 | Comparison to Phase 0 (no drift) |
| 6 | Commit message with evidence summary |

### Anti-Patterns

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| "Let me just quickly..." | Skips planning |
| "I'll document later" | Phase 6 never happens |
| "Tests can wait" | Phase 4 skipped |
| "I know what I'm doing" | Overconfidence |

## Implementation

### Phase Transition Protocol

Before moving to next phase:

1. **CHECK** — Is current phase complete?
2. **EVIDENCE** — What proves it's complete?
3. **DOCUMENT** — Record the evidence
4. **ADVANCE** — Only then move forward

### Corrective Runs

If Phase 4 (tests) fails:

1. Do NOT proceed to Phase 5
2. Return to Phase 2 with corrective scope
3. Document what went wrong
4. Add regression test for the failure

### Commit Message Pattern

```
feat(module): description

Phase 0: TODO plan in PR description
Phase 1: Baseline tests passed (17/17)
Phase 4: All tests green (23/23)
Phase 5: No scope drift from Phase 0
Phase 6: This commit

Files: file1.py, file2.py
Tests: test_file1.py, test_file2.py
```

## Consequences

### Positive
- Predictable, reviewable changes
- No scope creep
- Clear audit trail
- Fewer regressions

### Negative
- More upfront planning
- Feels slower (but prevents rework)

## Related
- ADR-0072: Diagnose Before Fix
- ADR-0073: Evidence-Based Claims
- ADR-0075: Ask Before Build
