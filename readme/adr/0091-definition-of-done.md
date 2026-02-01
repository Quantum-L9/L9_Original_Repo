# ADR-0091: Definition of Done (Enforceable)

**Status:** Accepted  
**Date:** 2026-02-01  
**Author:** Igor Beylin  
**Priority:** CRITICAL  
**Enforcement:** CI + Pre-commit + PR Template  

## Context

"Done" is not subjective. Work is either complete and verified, or it's not done. 

This ADR defines **concrete, checkable criteria** that determine when work is actually done — and **CI enforcement** to block incomplete work from merging.

## Decision

### Definition of Done Checklist

A change is **DONE** when ALL of the following are true:

```markdown
## ✅ DEFINITION OF DONE

### Code Complete
- [ ] All requested changes implemented
- [ ] No TODOs, FIXMEs, or placeholders left behind
- [ ] No commented-out code (unless documented why)

### Dependencies Traced
- [ ] `grep -r "<changed_entity>"` run
- [ ] All references to changed code updated
- [ ] Healthchecks updated (if config/auth changed)
- [ ] Environment variables documented (if added)

### Tests
- [ ] Unit tests pass: `pytest tests/unit/`
- [ ] Integration tests pass (if applicable)
- [ ] New tests written for new functionality
- [ ] Edge cases covered

### Verification Evidence
- [ ] Actual command output provided (not "should work")
- [ ] Exit code 0 shown
- [ ] Error conditions verified to not occur

### Documentation
- [ ] Docstrings added/updated
- [ ] README updated (if user-facing change)
- [ ] ADR created (if architectural decision)

### Security (if applicable)
- [ ] No secrets in code
- [ ] Auth changes include all consumers
- [ ] Firewall/network implications documented
```

### NOT DONE Examples

| Scenario | Why NOT DONE |
|----------|--------------|
| "Added --requirepass to Redis" | Healthcheck not updated → container fails |
| "Fixed the bug" | No test output shown → unverified |
| "Updated config" | Didn't grep for other references → incomplete |
| "Should work now" | No evidence → wishful thinking |
| "Tests pass locally" | No output shown → trust me bro |

### DONE Examples

| Scenario | Why DONE |
|----------|----------|
| "Added --requirepass, updated healthcheck, verified container starts" | All dependencies traced |
| "Fixed bug, test output: PASSED, exit 0" | Evidence provided |
| "Updated config, grep shows 3 references, all updated" | Downstream traced |

## Enforcement

### 1. CI Gate: `ci/check_definition_of_done.py`

```python
#!/usr/bin/env python3
"""
CI Check: Definition of Done Enforcement

Blocks PRs that don't meet DoD criteria:
1. No uncommitted TODOs/FIXMEs in diff
2. Changed auth/config → healthcheck also changed
3. PR description contains DoD checklist
4. Test evidence provided

Exit codes:
- 0: DoD met
- 1: DoD violations found
"""

PATTERNS_REQUIRING_HEALTHCHECK = [
    r"--requirepass",
    r"POSTGRES_PASSWORD",
    r"NEO4J_PASSWORD", 
    r"--auth",
]

INCOMPLETE_MARKERS = [
    r"# TODO:",
    r"# FIXME:",
    r"# HACK:",
    r"pass\s+# placeholder",
    r"raise NotImplementedError",
]
```

### 2. Pre-Commit Hook

```bash
#!/bin/bash
# Check for incomplete markers in staged files

if git diff --cached | grep -E "TODO:|FIXME:|HACK:|NotImplementedError"; then
    echo "❌ DoD VIOLATION: Incomplete markers found"
    echo "Remove TODOs/FIXMEs before committing or mark as intentional"
    exit 1
fi

# Check auth changes have corresponding healthcheck updates
if git diff --cached | grep -qE "requirepass|PASSWORD"; then
    if ! git diff --cached | grep -q "healthcheck"; then
        echo "⚠️ WARNING: Auth change detected without healthcheck update"
        echo "Verify healthchecks don't need updating"
    fi
fi
```

### 3. PR Template (`.github/PULL_REQUEST_TEMPLATE.md`)

```markdown
## Definition of Done

### Code Complete
- [ ] All changes implemented
- [ ] No TODOs/FIXMEs left

### Dependencies Traced
- [ ] `grep -r` run for changed entities
- [ ] All references updated

### Verification
```
<paste actual test output here>
```

### Checklist
- [ ] Tests pass
- [ ] Docs updated (if needed)
- [ ] Security reviewed (if auth/config change)
```

### 4. Agent Behavioral Rule

Added to `repeated-mistakes.md` as **Lesson #22**:

```markdown
### **22. DEFINITION OF DONE** 🔴 CRITICAL
**Rule:** Before claiming DONE, verify ALL DoD criteria met
**Checklist:**
1. Code complete (no TODOs)
2. Dependencies traced (grep -r)
3. Tests pass (show output)
4. Evidence provided (not "should work")
**ADR:** ADR-0091
```

## Consequences

### Positive
- Clear, objective "done" criteria
- CI blocks incomplete work
- No more "95% done" surprises
- Evidence required, not optional

### Negative
- Slightly more process overhead
- Must provide verification evidence
- Can't ship fast and break things

## Implementation

- [ ] Create `ci/check_definition_of_done.py`
- [ ] Update `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Add pre-commit hook for auth changes
- [ ] Add Lesson #22 to repeated-mistakes.md

## Related

- ADR-0000: Core Philosophy (100% Done)
- ADR-0073: Evidence-Based Claims
- Lesson #21: Trace All Dependencies
